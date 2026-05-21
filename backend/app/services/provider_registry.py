from __future__ import annotations

from app.models.model import Model
from app.services.mock_provider import MockProvider
from app.services.provider_base import LLMProvider
from app.services.real_deepseek_provider import DeepSeekProvider
from app.services.real_openai_provider import OpenAIProvider


# Singletons — providers are stateless, so one instance is enough.
_mock = MockProvider()
_openai = OpenAIProvider()
_deepseek = DeepSeekProvider()


def get_provider_for_model(model: Model, provider_name: str) -> LLMProvider:
    """Pick the appropriate provider implementation for a given DB model row.

    Dispatch is simple: `is_mock=True` always returns the mock; otherwise
    we match on `provider_name`. New providers register here.
    """
    if model.is_mock:
        return _mock

    if provider_name == "openai":
        return _openai
    if provider_name == "deepseek":
        return _deepseek

    from app.services.provider_base import ProviderError

    raise ProviderError(
        f"Provider '{provider_name}' is marked is_mock=False but no real implementation is wired yet",
        status_code=501,
        error_type="not_implemented",
        error_code="provider_not_wired",
    )
