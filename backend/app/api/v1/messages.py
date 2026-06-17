"""Anthropic Messages API 兼容端点 —— 支持 Claude Code。

Claude Code / Anthropic SDK 走 `POST /v1/messages`(Anthropic 格式,x-api-key 鉴权),
与 OpenAI 的 /chat/completions 不同。这里做**透传代理**:校验我方 key + 额度,
把请求原样转发到上游 aicodewith 的 Anthropic 端点(注入上游 key),响应/流式原样回传,
事后按 usage 的 token 计 ¥扣费。无上游 key 时回落 mock,便于本地/测试端到端跑通。

透传(而非翻译 Anthropic↔OpenAI)的好处:工具调用、流式、内容块全部由上游原生处理,
对 Claude Code 保真;我方只管鉴权与计费。
"""
from __future__ import annotations

import json
import time
import uuid

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.models.model import Model
from app.models.usage_record import UsageRecord
from app.services.auth_service import verify_api_key
from app.services.billing_engine import calculate_cost, check_budget, record_usage_cost
from app.services.membership import check_user_credit, deduct_user_credit
from app.services.mock_provider import estimate_tokens

router = APIRouter()

ANTHROPIC_VERSION = "2023-06-01"


def _auth(authorization, x_api_key, db):
    # Claude Code 发 x-api-key;也兼容 Authorization: Bearer
    token = x_api_key or (authorization[7:] if authorization and authorization.startswith("Bearer ") else None)
    if not token:
        raise HTTPException(status_code=401, detail="缺少 API key(x-api-key 或 Authorization: Bearer）")
    return verify_api_key("Bearer " + token, db)


def _billing_model(db: Session, model_name: str) -> Model:
    m = db.query(Model).filter(Model.name == model_name).first()
    if m:
        return m
    m = db.query(Model).filter(Model.name == "claude-code").first()
    return m or db.query(Model).first()


def _record(db, *, api_key_id, model, prompt_tokens, completion_tokens, latency_ms, status):
    cost = calculate_cost(model, prompt_tokens, completion_tokens) if status == "success" else 0.0
    db.add(UsageRecord(
        request_id=str(uuid.uuid4()), api_key_id=api_key_id, model_id=model.id,
        provider_id=model.provider_id, routing_strategy="anthropic-passthrough",
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens, latency_ms=latency_ms,
        cost_usd=cost, status=status,
    ))
    if status == "success" and cost > 0:
        record_usage_cost(db, api_key_id, cost)
        deduct_user_credit(db, api_key_id, cost)
    db.commit()


def _prompt_text(body) -> str:
    out = []
    sys = body.get("system")
    if isinstance(sys, str):
        out.append(sys)
    elif isinstance(sys, list):
        out += [b.get("text", "") for b in sys if isinstance(b, dict)]
    for m in body.get("messages") or []:
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            out += [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
    return " ".join(out)


def _parse_usage(text, in_tok, out_tok):
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        try:
            d = json.loads(line[5:].strip())
        except Exception:
            continue
        u = d.get("usage") or (d.get("message") or {}).get("usage") or {}
        if u.get("input_tokens"):
            in_tok = u["input_tokens"]
        if u.get("output_tokens"):
            out_tok = u["output_tokens"]
    return in_tok, out_tok


@router.post("/messages")
async def anthropic_messages(
    request: Request,
    db: Session = Depends(get_db),
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="x-api-key"),
    anthropic_version: str = Header(None, alias="anthropic-version"),
):
    api_key = _auth(authorization, x_api_key, db)
    body = await request.json()
    model_name = body.get("model") or "claude-code"
    stream = bool(body.get("stream"))
    bill_model = _billing_model(db, model_name)

    est = estimate_tokens(_prompt_text(body))
    check_budget(db, api_key.id, calculate_cost(bill_model, est, est))
    check_user_credit(db, api_key)

    start = time.time()
    use_mock = (not settings.AICODEWITH_API_KEY) and settings.MOCK_WHEN_NO_UPSTREAM_KEY

    # ── 无上游 key:回落 mock(Anthropic 格式)──
    if use_mock:
        text = "[mock] Claude Code 透传通路已就绪。配置 AICODEWITH_API_KEY 与 AICODEWITH_ANTHROPIC_BASE_URL 后即转真实上游。"
        out_tok = estimate_tokens(text)
        mid = "msg_" + uuid.uuid4().hex[:24]
        if stream:
            def ev(t, d):
                return f"event: {t}\ndata: {json.dumps(d)}\n\n"
            async def gen():
                yield ev("message_start", {"type": "message_start", "message": {"id": mid, "type": "message", "role": "assistant", "model": model_name, "content": [], "stop_reason": None, "usage": {"input_tokens": est, "output_tokens": 0}}})
                yield ev("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}})
                yield ev("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}})
                yield ev("content_block_stop", {"type": "content_block_stop", "index": 0})
                yield ev("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": out_tok}})
                yield ev("message_stop", {"type": "message_stop"})
                _record(db, api_key_id=api_key.id, model=bill_model, prompt_tokens=est, completion_tokens=out_tok, latency_ms=int((time.time() - start) * 1000), status="success")
            return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
        _record(db, api_key_id=api_key.id, model=bill_model, prompt_tokens=est, completion_tokens=out_tok, latency_ms=int((time.time() - start) * 1000), status="success")
        return JSONResponse({"id": mid, "type": "message", "role": "assistant", "model": model_name, "content": [{"type": "text", "text": text}], "stop_reason": "end_turn", "stop_sequence": None, "usage": {"input_tokens": est, "output_tokens": out_tok}})

    # ── 透传到上游 Anthropic 端点 ──
    url = settings.AICODEWITH_ANTHROPIC_BASE_URL.rstrip("/") + "/v1/messages"
    headers = {"x-api-key": settings.AICODEWITH_API_KEY, "anthropic-version": anthropic_version or ANTHROPIC_VERSION, "content-type": "application/json"}
    timeout = settings.AICODEWITH_TIMEOUT_SECONDS

    if stream:
        async def proxy():
            in_tok, out_tok, status = est, 0, "success"
            buf = b""
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    async with client.stream("POST", url, headers=headers, json=body) as r:
                        async for chunk in r.aiter_bytes():
                            buf += chunk
                            yield chunk
            except Exception as e:  # noqa: BLE001
                status = "error"
                yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'upstream_error', 'message': str(e)}})}\n\n".encode()
            in_tok, out_tok = _parse_usage(buf.decode("utf-8", "ignore"), in_tok, out_tok)
            _record(db, api_key_id=api_key.id, model=bill_model, prompt_tokens=in_tok, completion_tokens=out_tok, latency_ms=int((time.time() - start) * 1000), status=status)
        return StreamingResponse(proxy(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, headers=headers, json=body)
        data = r.json()
    except Exception as e:  # noqa: BLE001
        _record(db, api_key_id=api_key.id, model=bill_model, prompt_tokens=est, completion_tokens=0, latency_ms=int((time.time() - start) * 1000), status="error")
        return JSONResponse(status_code=502, content={"type": "error", "error": {"type": "upstream_error", "message": str(e)}})

    ok = r.status_code < 400
    u = data.get("usage") or {}
    _record(db, api_key_id=api_key.id, model=bill_model, prompt_tokens=u.get("input_tokens", est), completion_tokens=u.get("output_tokens", 0), latency_ms=int((time.time() - start) * 1000), status="success" if ok else "error")
    return JSONResponse(status_code=r.status_code, content=data)
