from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_api_key
from app.models.api_key import ApiKey
from app.models.model import Model
from app.models.usage_record import UsageRecord
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from app.services.routing_engine import route_request, try_fallback
from app.services.mock_provider import generate_mock_response, generate_mock_stream, estimate_tokens
from app.services.billing_engine import calculate_cost, check_budget, record_usage_cost
from app.services.circuit_breaker import circuit_breaker

router = APIRouter()


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    db: Session = Depends(get_db),
    api_key: ApiKey = Depends(get_current_api_key),
    x_routing_strategy: str = Header(default="balanced"),
    x_industry: str = Header(default=""),
    x_task_type: str = Header(default=""),
    x_model_override: str = Header(default=""),
):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Use model from request body or override header
    model_override = x_model_override or request.model or ""

    # Route the request
    decision = route_request(
        db=db,
        strategy=x_routing_strategy,
        industry=x_industry,
        task_type=x_task_type,
        model_override=model_override,
    )

    # Get model details for billing
    model = db.query(Model).filter(Model.id == decision.model_id).first()
    if not model:
        raise HTTPException(status_code=500, detail="Routed model not found")

    # Budget pre-check (estimate based on input tokens)
    prompt_text = " ".join(m.content for m in request.messages)
    est_prompt_tokens = estimate_tokens(prompt_text)
    est_cost = calculate_cost(model, est_prompt_tokens, est_prompt_tokens)  # rough estimate
    check_budget(db, api_key.id, est_cost)

    # Stream mode
    if request.stream:
        async def stream_with_usage():
            completion_tokens = 0
            async for chunk in generate_mock_stream(decision.model_name, request.messages):
                if "content" in chunk:
                    words = chunk.count(" ") + 1
                    completion_tokens += int(words * 0.3)
                yield chunk

            # Record usage after stream completes
            latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens = estimate_tokens(prompt_text)
            final_completion_tokens = max(completion_tokens, 20)
            cost = calculate_cost(model, prompt_tokens, final_completion_tokens)

            usage = UsageRecord(
                request_id=request_id,
                api_key_id=api_key.id,
                model_id=model.id,
                provider_id=model.provider_id,
                routing_strategy=decision.strategy_used,
                industry=x_industry,
                task_type=x_task_type,
                was_fallback=decision.was_fallback,
                prompt_tokens=prompt_tokens,
                completion_tokens=final_completion_tokens,
                total_tokens=prompt_tokens + final_completion_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                status="success",
            )
            db.add(usage)
            record_usage_cost(db, api_key.id, cost)
            db.commit()

        return StreamingResponse(
            stream_with_usage(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-stream mode
    try:
        response_data = generate_mock_response(decision.model_name, request.messages)
        circuit_breaker.record_success(decision.provider_id)
    except Exception as e:
        circuit_breaker.record_failure(decision.provider_id)
        # Try fallback
        fallback_decision = try_fallback(db, decision.fallback_chain)
        if fallback_decision:
            decision = fallback_decision
            model = db.query(Model).filter(Model.id == decision.model_id).first()
            response_data = generate_mock_response(decision.model_name, request.messages)
        else:
            raise HTTPException(status_code=502, detail=f"All providers failed: {str(e)}")

    latency_ms = int((time.time() - start_time) * 1000)
    # Use actual latency from mock (simulated)
    latency_ms = max(latency_ms, response_data.get("latency_ms", latency_ms))

    prompt_tokens = response_data["usage"]["prompt_tokens"]
    completion_tokens = response_data["usage"]["completion_tokens"]
    cost = calculate_cost(model, prompt_tokens, completion_tokens)

    # Record usage
    usage = UsageRecord(
        request_id=request_id,
        api_key_id=api_key.id,
        model_id=model.id,
        provider_id=model.provider_id,
        routing_strategy=decision.strategy_used,
        industry=x_industry,
        task_type=x_task_type,
        was_fallback=decision.was_fallback,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost,
        status="success",
    )
    db.add(usage)
    record_usage_cost(db, api_key.id, cost)
    db.commit()

    # Build response
    response_data.pop("latency_ms", None)
    response_data["x_routing_strategy"] = decision.strategy_used
    response_data["x_provider"] = model.name
    response_data["x_cost_usd"] = cost
    response_data["x_latency_ms"] = latency_ms

    return response_data
