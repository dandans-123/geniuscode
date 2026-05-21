from __future__ import annotations

import json
import time
import uuid
from typing import AsyncIterator

from app.config import settings
from app.schemas.chat import ChatMessage
from app.services.provider_base import ProviderError


# Lazy import — the SDK is only required when this provider is actually
# instantiated, so tests that monkey-patch can run without the real SDK
# at import time.
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

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ProviderError(
            "OPENAI_API_KEY is not configured",
            status_code=500,
            error_type="configuration_error",
            error_code="missing_api_key",
        )
    return AsyncOpenAI(api_key=api_key, timeout=settings.OPENAI_TIMEOUT_SECONDS)


def _messages_to_openai(messages: list[ChatMessage]) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _translate_openai_error(exc: Exception) -> ProviderError:
    """Map openai SDK exceptions to a sanitized `ProviderError`.

    We intentionally do not bubble the raw exception out so internal
    tracebacks / request IDs / partial auth headers cannot leak.
    """
    # Import inside the function so the module can be imported without the SDK.
    try:
        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            NotFoundError,
            PermissionDeniedError,
            RateLimitError,
            APIStatusError,
        )
    except ImportError:
        return ProviderError(f"upstream openai error: {exc.__class__.__name__}")

    if isinstance(exc, AuthenticationError):
        return ProviderError(
            "OpenAI authentication failed",
            status_code=401,
            error_type="authentication_error",
            error_code="invalid_api_key",
        )
    if isinstance(exc, PermissionDeniedError):
        return ProviderError(
            "OpenAI permission denied",
            status_code=403,
            error_type="permission_error",
            error_code="permission_denied",
        )
    if isinstance(exc, RateLimitError):
        return ProviderError(
            "OpenAI rate limit exceeded",
            status_code=429,
            error_type="rate_limit_error",
            error_code="rate_limited",
        )
    if isinstance(exc, BadRequestError):
        return ProviderError(
            "OpenAI rejected the request",
            status_code=400,
            error_type="invalid_request_error",
            error_code="bad_request",
        )
    if isinstance(exc, NotFoundError):
        return ProviderError(
            "Requested OpenAI model was not found",
            status_code=404,
            error_type="invalid_request_error",
            error_code="model_not_found",
        )
    if isinstance(exc, APITimeoutError):
        return ProviderError(
            "OpenAI request timed out",
            status_code=504,
            error_type="upstream_timeout",
            error_code="timeout",
        )
    if isinstance(exc, APIConnectionError):
        return ProviderError(
            "Could not reach OpenAI",
            status_code=502,
            error_type="upstream_error",
            error_code="connection_error",
        )
    if isinstance(exc, APIStatusError):
        # 5xx and other status errors — preserve status_code but scrub body.
        return ProviderError(
            f"OpenAI returned status {exc.status_code}",
            status_code=exc.status_code if exc.status_code >= 400 else 502,
            error_type="upstream_error",
            error_code="status_error",
        )

    return ProviderError(
        f"upstream openai error: {exc.__class__.__name__}",
        status_code=502,
        error_type="upstream_error",
    )


class OpenAIProvider:
    """Real OpenAI provider — used for models with `is_mock=False`."""

    name = "openai"

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

        # SDK returns a pydantic-like object; convert to plain dict so the
        # downstream code (which expects dicts from the mock) keeps working.
        data = resp.model_dump()
        # Normalize usage shape — the SDK may omit fields on some responses.
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
            # Ask the API to include usage in the final chunk so we can bill
            # accurately without re-estimating from chunk text.
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
                # Convert SDK ChatCompletionChunk into SSE wire format.
                payload = chunk.model_dump()
                yield f"data: {json.dumps(payload)}\n\n"
        except Exception as exc:  # noqa: BLE001
            err = _translate_openai_error(exc)
            yield f"data: {json.dumps(err.to_openai_error(self.name))}\n\n"

        yield "data: [DONE]\n\n"
