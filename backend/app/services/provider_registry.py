from __future__ import annotations

from app.models.model import Model
from app.services.mock_provider import MockProvider
from app.services.provider_base import LLMProvider
from app.services.real_openai_provider import OpenAIProvider


# Singletons — providers are stateless, so one instance is enough.
_mock = MockProvider()
_openai = OpenAIProvider()


def get_provider_for_model(model: Model, provider_name: str) -> LLMProvider:
    """Pick the appropriate provider implementation for a given DB model row.

    Dispatch is intentionally simple: `is_mock=True` always returns the
    mock; `is_mock=False` returns the real provider whose name matches
    the model's provider row (currently only `openai` is wired —
    DeepSeek/etc. land in later tasks).
    """
    if model.is_mock:
        return _mock

    if provider_name == "openai":
        return _openai

    # Real provider requested but not yet implemented — fall back to mock
    # would be silently misleading, so explicitly raise. The HTTP layer
    # converts this into a 501.
    from app.services.provider_base import ProviderError

    raise ProviderError(
        f"Provider '{provider_name}' is marked is_mock=False but no real implementation is wired yet",
        status_code=501,
        error_type="not_implemented",
        error_code="provider_not_wired",
    )
