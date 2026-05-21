from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_api_key
from app.models.api_key import ApiKey
from app.models.model import Model
from app.models.provider import Provider
from app.models.usage_record import UsageRecord
from app.schemas.chat import ChatCompletionRequest
from app.services.routing_engine import route_request
from app.services.mock_provider import estimate_tokens
from app.services.billing_engine import calculate_cost, check_budget, record_usage_cost
from app.services.circuit_breaker import circuit_breaker
from app.services.provider_base import ProviderError
from app.services.provider_registry import get_provider_for_model

router = APIRouter()


def _record_usage(
    db: Session,
    *,
    request_id: str,
    api_key_id: int,
    model: Model,
    decision,
    industry: str,
    task_type: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: int,
    cost: float,
    status: str,
) -> None:
    usage = UsageRecord(
        request_id=request_id,
        api_key_id=api_key_id,
        model_id=model.id,
        provider_id=model.provider_id,
        routing_strategy=decision.strategy_used,
        industry=industry,
        task_type=task_type,
        was_fallback=decision.was_fallback,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=latency_ms,
        cost_usd=cost,
        status=status,
    )
    db.add(usage)
    if status == "success" and cost > 0:
        record_usage_cost(db, api_key_id, cost)
    db.commit()


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

    provider_row = db.query(Provider).filter(Provider.id == model.provider_id).first()
    provider_name = provider_row.name if provider_row else "unknown"

    # Pick the actual implementation (mock vs real) for this model.
    try:
        provider = get_provider_for_model(model, provider_name)
    except ProviderError as e:
        return JSONResponse(
            status_code=e.status_code, content=e.to_openai_error(provider_name)
        )

    # Budget pre-check (estimate based on input tokens)
    prompt_text = " ".join(m.content for m in request.messages)
    est_prompt_tokens = estimate_tokens(prompt_text)
    est_cost = calculate_cost(model, est_prompt_tokens, est_prompt_tokens)  # rough estimate
    check_budget(db, api_key.id, est_cost)

    # Stream mode
    if request.stream:
        async def stream_with_usage():
            completion_tokens = 0
            prompt_tokens_final = estimate_tokens(prompt_text)
            stream_status = "success"
            try:
                async for chunk in provider.stream(
                    decision.model_name,
                    request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                ):
                    # Try to surface real usage if the provider includes it.
                    if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                        try:
                            payload = json.loads(chunk[len("data: "):].strip())
                            if isinstance(payload, dict):
                                usage = payload.get("usage") or {}
                                if usage.get("completion_tokens"):
                                    completion_tokens = usage["completion_tokens"]
                                if usage.get("prompt_tokens"):
                                    prompt_tokens_final = usage["prompt_tokens"]
                                # Fall back to chunk-text estimation when
                                # provider does not include usage.
                                if not usage:
                                    choices = payload.get("choices") or []
                                    for c in choices:
                                        delta = c.get("delta") or {}
                                        content = delta.get("content") or ""
                                        if content:
                                            completion_tokens += estimate_tokens(content)
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass
                    yield chunk
                circuit_breaker.record_success(decision.provider_id)
            except ProviderError as e:
                circuit_breaker.record_failure(decision.provider_id)
                stream_status = "error"
                yield f"data: {json.dumps(e.to_openai_error(provider_name))}\n\n"
                yield "data: [DONE]\n\n"

            # Record usage after stream completes (success OR error)
            latency_ms = int((time.time() - start_time) * 1000)
            final_completion_tokens = (
                completion_tokens if stream_status == "success" else 0
            )
            cost = (
                calculate_cost(model, prompt_tokens_final, final_completion_tokens)
                if stream_status == "success"
                else 0.0
            )
            _record_usage(
                db,
                request_id=request_id,
                api_key_id=api_key.id,
                model=model,
                decision=decision,
                industry=x_industry,
                task_type=x_task_type,
                prompt_tokens=prompt_tokens_final,
                completion_tokens=final_completion_tokens,
                latency_ms=latency_ms,
                cost=cost,
                status=stream_status,
            )

        return StreamingResponse(
            stream_with_usage(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # Non-stream mode — no automatic fallback yet (Task 5+6). One provider, one shot.
    try:
        response_data = await provider.complete(
            decision.model_name,
            request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
        )
        circuit_breaker.record_success(decision.provider_id)
    except ProviderError as e:
        circuit_breaker.record_failure(decision.provider_id)
        _record_usage(
            db,
            request_id=request_id,
            api_key_id=api_key.id,
            model=model,
            decision=decision,
            industry=x_industry,
            task_type=x_task_type,
            prompt_tokens=estimate_tokens(prompt_text),
            completion_tokens=0,
            latency_ms=int((time.time() - start_time) * 1000),
            cost=0.0,
            status="error",
        )
        return JSONResponse(
            status_code=e.status_code, content=e.to_openai_error(provider_name)
        )

    latency_ms = int((time.time() - start_time) * 1000)
    # Use actual latency reported by provider when larger (mock simulates latency)
    latency_ms = max(latency_ms, response_data.get("latency_ms", latency_ms))

    prompt_tokens = response_data["usage"]["prompt_tokens"]
    completion_tokens = response_data["usage"]["completion_tokens"]
    cost = calculate_cost(model, prompt_tokens, completion_tokens)

    _record_usage(
        db,
        request_id=request_id,
        api_key_id=api_key.id,
        model=model,
        decision=decision,
        industry=x_industry,
        task_type=x_task_type,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        cost=cost,
        status="success",
    )

    # Build response (strip internal-only fields, add ModelMux extension fields)
    response_data.pop("latency_ms", None)
    response_data["x_routing_strategy"] = decision.strategy_used
    response_data["x_provider"] = model.name
    response_data["x_cost_usd"] = cost
    response_data["x_latency_ms"] = latency_ms

    return response_data
