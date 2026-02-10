"""Factory for creating LLM providers."""

from typing import Optional, Dict, Type

from .base import LLMProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider, DeepseekProvider
from .gemini_provider import GeminiProvider


# Registry of available providers
PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,
    "openai": OpenAIProvider,
    "gpt": OpenAIProvider,
    "gemini": GeminiProvider,
    "google": GeminiProvider,
    "deepseek": DeepseekProvider,
}

# Model to provider mapping for auto-detection
MODEL_PROVIDERS: Dict[str, str] = {
    # Anthropic
    "claude": "anthropic",
    "claude-sonnet": "anthropic",
    "claude-opus": "anthropic",
    "claude-haiku": "anthropic",
    "sonnet": "anthropic",
    "opus": "anthropic",
    "haiku": "anthropic",
    # OpenAI
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-4": "openai",
    "gpt-3.5-turbo": "openai",
    "o1": "openai",
    "o1-mini": "openai",
    # Gemini
    "gemini": "gemini",
    "gemini-pro": "gemini",
    "gemini-flash": "gemini",
    "gemini-2.5-flash": "gemini",
    "gemini-2.5-pro": "gemini",
    "gemini-2.0-flash": "gemini",
    "gemini-2.0-flash-lite": "gemini",
    # Deepseek
    "deepseek": "deepseek",
    "deepseek-chat": "deepseek",
    "deepseek-coder": "deepseek",
    "deepseek-reasoner": "deepseek",
}


def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Get an LLM provider instance.

    Args:
        provider_name: Explicit provider name (anthropic, openai, gemini, deepseek)
        model: Model name - if provided without provider, will auto-detect provider

    Returns:
        LLMProvider instance

    Examples:
        # Explicit provider
        get_provider("anthropic")
        get_provider("openai")
        get_provider("gemini")
        get_provider("deepseek")

        # Auto-detect from model
        get_provider(model="gpt-4o")  # Returns OpenAI provider
        get_provider(model="claude-sonnet")  # Returns Anthropic provider
        get_provider(model="gemini-pro")  # Returns Gemini provider

        # Default (Anthropic)
        get_provider()
    """
    # If provider explicitly specified
    if provider_name:
        provider_key = provider_name.lower()
        if provider_key not in PROVIDERS:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available: {list(PROVIDERS.keys())}"
            )
        return PROVIDERS[provider_key]()

    # Try to detect from model name
    if model:
        model_lower = model.lower()
        for prefix, provider in MODEL_PROVIDERS.items():
            if model_lower.startswith(prefix):
                return PROVIDERS[provider]()

    # Default to Anthropic
    return AnthropicProvider()


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
