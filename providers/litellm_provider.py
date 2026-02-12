"""LiteLLM-backed provider (Phase 2). Single implementation for all LLM calls."""

from typing import Optional

from .base import LLMProvider, LLMResponse


# LiteLLM model strings: provider/model-name (OpenAI can omit prefix)
# Do not use deprecated IDs (gemini-1.5-flash, gemini-2.0-flash-exp, etc.)
DEFAULT_MODELS = {
    "anthropic": "anthropic/claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
    "gemini": "gemini/gemini-2.0-flash",
    "deepseek": "deepseek/deepseek-chat",
}

# Map provider + optional model -> LiteLLM model string
MODEL_ALIASES = {
    "anthropic": {
        None: "anthropic/claude-sonnet-4-20250514",
        "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
        "claude-opus": "anthropic/claude-opus-4-20250514",
        "claude-haiku": "anthropic/claude-3-5-haiku-20241022",
    },
    "openai": {
        None: "gpt-4o-mini",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-4": "gpt-4",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
        "o1": "o1",
        "o1-mini": "o1-mini",
    },
    "gemini": {
        None: "gemini/gemini-2.0-flash",
        "gemini-2.0-flash": "gemini/gemini-2.0-flash",
        "gemini-2.5-flash": "gemini/gemini-2.5-flash",
        "gemini-2.5-pro": "gemini/gemini-2.5-pro",
    },
    "deepseek": {
        None: "deepseek/deepseek-chat",
        "deepseek-chat": "deepseek/deepseek-chat",
        "deepseek-coder": "deepseek/deepseek-coder",
        "deepseek-reasoner": "deepseek/deepseek-reasoner",
    },
}


def _to_litellm_model(provider_name: Optional[str], model: Optional[str]) -> str:
    """Map provider + model to LiteLLM model string."""
    if provider_name:
        key = provider_name.lower()
        if key in ("claude", "gpt", "google"):
            key = "anthropic" if key == "claude" else "openai" if key == "gpt" else "gemini"
        if key in MODEL_ALIASES:
            aliases = MODEL_ALIASES[key]
            if model:
                model_lower = model.lower()
                # Prefer longest alias match first (e.g. gpt-4o-mini before gpt-4o)
                for alias in sorted((a for a in aliases if a), key=len, reverse=True):
                    if model_lower == alias or model_lower.startswith(alias + "-") or model_lower.startswith(alias + "."):
                        return aliases[alias]
                # no alias match: use provider prefix + model for non-OpenAI
                if key == "openai":
                    return model  # OpenAI often works without prefix
                if key in ("anthropic", "gemini", "deepseek"):
                    return f"{key}/{model}"
            return aliases.get(None, DEFAULT_MODELS.get(key, "gpt-4o-mini"))
    if model:
        model_lower = model.lower()
        for _prov, aliases in MODEL_ALIASES.items():
            for alias in sorted((a for a in aliases if a), key=len, reverse=True):
                if model_lower == alias or model_lower.startswith(alias + "-") or model_lower.startswith(alias + "."):
                    return aliases[alias]
        return model
    return DEFAULT_MODELS.get("openai", "gpt-4o-mini")


class LiteLLMProvider(LLMProvider):
    """Single provider that delegates to litellm.completion()."""

    def __init__(self, default_model: str, metadata: Optional[dict] = None):
        """Initialize with the LiteLLM model string to use by default.

        Args:
            default_model: LiteLLM model string (e.g. gpt-4o-mini, anthropic/claude-sonnet-4-20250514).
            metadata: Optional dict passed to litellm (e.g. agent, tier) for cost logging.
        """
        self._default_model = default_model
        self._metadata = metadata or {}

    @property
    def name(self) -> str:
        return "litellm"

    @property
    def default_model(self) -> str:
        return self._default_model

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import litellm

        resolved_model = model or self._default_model
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        kwargs = {
            "model": resolved_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "metadata": {**self._metadata},
        }
        response = litellm.completion(**kwargs)

        content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) or (usage or {}).get("prompt_tokens", 0)
        output_tokens = getattr(usage, "completion_tokens", 0) or (usage or {}).get("completion_tokens", 0)
        hidden = getattr(response, "_hidden_params", None) or {}
        cost = float(hidden.get("response_cost", 0) or 0)
        model_id = getattr(response, "model", None) or resolved_model

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model_id,
            provider=self.name,
            cost=cost,
        )

    def is_available(self) -> bool:
        """LiteLLM reads API keys from env; we consider it available if the model is set."""
        return bool(self._default_model)
