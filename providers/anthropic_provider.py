"""Anthropic (Claude) provider implementation."""

import os
from typing import Optional

from .base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic Claude models."""

    MODELS = {
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-opus": "claude-opus-4-20250514",
        "claude-haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
        "haiku": "claude-3-5-haiku-20241022",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key. Uses ANTHROPIC_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def default_model(self) -> str:
        return "claude-sonnet-4-20250514"

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to full model name."""
        if model is None:
            return self.default_model
        return self.MODELS.get(model, model)

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()
        resolved_model = self._resolve_model(model)

        response = client.messages.create(
            model=resolved_model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return LLMResponse(
            content=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=resolved_model,
            provider=self.name,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
