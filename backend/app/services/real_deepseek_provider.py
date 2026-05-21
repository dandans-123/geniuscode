"""DeepSeek provider — OpenAI-SDK-compatible upstream.

DeepSeek's chat API is OpenAI-compatible, so we reuse the `openai`
SDK's `AsyncOpenAI` client with a different `base_url`. Error
translation logic is shared with `real_openai_provider` since the
SDK raises the same exception types regardless of upstream.
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

    api_key = settings.DEEPSEEK_API_KEY
    if not api_key:
        raise ProviderError(
            "DEEPSEEK_API_KEY is not configured",
            status_code=500,
            error_type="configuration_error",
            error_code="missing_api_key",
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=settings.DEEPSEEK_BASE_URL,
        timeout=settings.DEEPSEEK_TIMEOUT_SECONDS,
    )


class DeepSeekProvider:
    """Real DeepSeek provider — used for DeepSeek models with `is_mock=False`."""

    name = "deepseek"

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
