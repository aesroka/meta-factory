"""Factory for creating LLM providers (Phase 2: LiteLLM-backed)."""

import os
from typing import Optional, Dict

from .base import LLMProvider
from .litellm_provider import LiteLLMProvider, _to_litellm_model

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
    """List all providers and their availability (via env keys)."""
    # LiteLLM uses GOOGLE_API_KEY for Gemini (Google AI Studio)
    keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "google": "GOOGLE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    result = {}
    seen = set()
    for name, env_var in keys.items():
        if name in seen:
            continue
        if name == "google":
            continue
        seen.add(name)
        result[name] = bool(os.environ.get(env_var, "").strip())
    return result
