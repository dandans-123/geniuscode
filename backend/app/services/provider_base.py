from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from app.schemas.chat import ChatMessage


class ProviderError(Exception):
    """Raised by a provider when an upstream call fails.

    The HTTP layer translates this into an OpenAI-style error JSON. Internal
    tracebacks are *not* leaked to the client.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        error_type: str = "upstream_error",
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.error_code = error_code

    def to_openai_error(self, provider_name: str) -> dict:
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "code": self.error_code,
                "param": None,
                "provider": provider_name,
            }
        }


@runtime_checkable
class LLMProvider(Protocol):
    """Minimal interface every provider (mock or real) must implement.

    `complete` returns an OpenAI-format response dict.
    `stream`   yields SSE-formatted `data: {...}\n\n` strings, terminating
    with `data: [DONE]\n\n` — matching the OpenAI streaming contract.
    """

    name: str

    async def complete(
        self,
        model_name: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> dict: ...

    def stream(
        self,
        model_name: str,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float = 1.0,
    ) -> AsyncIterator[str]: ...
