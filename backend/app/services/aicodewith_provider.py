"""aicodewith 上游 Provider — OpenAI 兼容中转。

GeniusCode 的唯一上游是 aicodewith(它本身就是一个 OpenAI 兼容的多模型中转）。
所有模型的 `model.name` 直接透传给 aicodewith，因此这里复用 `openai` SDK 的
`AsyncOpenAI` 客户端，只换 `base_url` 和 `api_key`，错误翻译逻辑与
`real_openai_provider` 共用。

接入前需在 `.env` 配置：
  AICODEWITH_API_KEY   —— aicodewith 控制台签发的 key
  AICODEWITH_BASE_URL  —— aicodewith 的 OpenAI 兼容端点（以其文档为准）
"""
from __future__ import annotations

import json
import time
from typing import AsyncIterator

from app.config import settings
from app.schemas.chat import ChatMessage
from app.services.provider_base import ProviderError
from app.services.real_openai_provider import (
    _messages_to_openai,
    _translate_openai_error,
)


def _client():
    try:
        from openai import AsyncOpenAI
    except ImportError as e:  # pragma: no cover — install-time guard
        raise ProviderError(
            "openai SDK is not installed; run `pip install -r requirements.txt`",
            status_code=500,
            error_type="configuration_error",
            error_code="sdk_missing",
        ) from e

    api_key = settings.AICODEWITH_API_KEY
    if not api_key:
        raise ProviderError(
            "AICODEWITH_API_KEY is not configured（上游 aicodewith 的 key 尚未配置）",
            status_code=500,
            error_type="configuration_error",
            error_code="missing_api_key",
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=settings.AICODEWITH_BASE_URL,
        timeout=settings.AICODEWITH_TIMEOUT_SECONDS,
    )


class AicodewithProvider:
    """真实上游 Provider —— 用于所有 is_mock=False 的模型，统一转发到 aicodewith。"""

    name = "aicodewith"

    async def complete(
        self,
        model_name: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict:
        client = _client()
        kwargs: dict = {
            "model": model_name,
            "messages": _messages_to_openai(messages),
            "temperature": temperature,
            "top_p": top_p,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        start = time.time()
        try:
            resp = await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 — translated, then re-raised
            raise _translate_openai_error(exc) from None

        latency_ms = int((time.time() - start) * 1000)

        data = resp.model_dump()
        usage = data.get("usage") or {}
        data["usage"] = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
        data["latency_ms"] = latency_ms
        return data

    async def stream(
        self,
        model_name: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> AsyncIterator[str]:
        client = _client()
        kwargs: dict = {
            "model": model_name,
            "messages": _messages_to_openai(messages),
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        try:
            sse_stream = await client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise _translate_openai_error(exc) from None

        try:
            async for chunk in sse_stream:
                payload = chunk.model_dump()
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception as exc:  # noqa: BLE001
            err = _translate_openai_error(exc)
            yield f"data: {json.dumps(err.to_openai_error(self.name))}\n\n"

        yield "data: [DONE]\n\n"
