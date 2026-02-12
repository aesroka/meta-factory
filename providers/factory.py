"""Factory for creating LLM providers (Phase 2: LiteLLM-backed)."""

from typing import Optional, Dict, Type

from .base import LLMProvider
from .litellm_provider import LiteLLMProvider, _to_litellm_model

# Legacy providers kept but unused (can remove after Phase 2 verified)
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider, DeepseekProvider
from .gemini_provider import GeminiProvider

# Registry for list_providers (availability check still uses legacy for now)
PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,
    "openai": OpenAIProvider,
    "gpt": OpenAIProvider,
    "gemini": GeminiProvider,
    "google": GeminiProvider,
    "deepseek": DeepseekProvider,
}

MODEL_PROVIDERS: Dict[str, str] = {
    "claude": "anthropic",
    "claude-sonnet": "anthropic",
    "claude-opus": "anthropic",
    "claude-haiku": "anthropic",
    "sonnet": "anthropic",
    "opus": "anthropic",
    "haiku": "anthropic",
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4": "openai",
    "gpt-3.5-turbo": "openai",
    "o1": "openai",
    "o1-mini": "openai",
    "gemini": "gemini",
    "gemini-pro": "gemini",
    "gemini-flash": "gemini",
    "gemini-2.5-flash": "gemini",
    "gemini-2.5-pro": "gemini",
    "gemini-2.0-flash": "gemini",
    "gemini-2.0-flash-lite": "gemini",
    "deepseek": "deepseek",
    "deepseek-chat": "deepseek",
    "deepseek-coder": "deepseek",
    "deepseek-reasoner": "deepseek",
}


def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Return a LiteLLM-backed provider with the resolved model string."""
    litellm_model = _to_litellm_model(provider_name, model)
    return LiteLLMProvider(default_model=litellm_model)


def list_providers() -> Dict[str, bool]:
    """List all providers and their availability.

    Returns:
        Dict mapping provider name to availability status
    """
    result = {}
    for name, provider_class in PROVIDERS.items():
        # Skip aliases
        if name in ["claude", "gpt", "google"]:
            continue
        try:
            provider = provider_class()
            result[name] = provider.is_available()
        except Exception:
            result[name] = False
    return result
