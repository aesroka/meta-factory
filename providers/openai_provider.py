"""OpenAI provider implementation."""

import os
from typing import Optional

from .base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models."""

    MODELS = {
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-4-turbo": "gpt-4-turbo",
        "gpt-4": "gpt-4",
        "gpt-3.5-turbo": "gpt-3.5-turbo",
        "o1": "o1",
        "o1-mini": "o1-mini",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. Uses OPENAI_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o"

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def _resolve_model(self, model: Optional[str]) -> str:
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

        response = client.chat.completions.create(
            model=resolved_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=resolved_model,
            provider=self.name,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)


class DeepseekProvider(LLMProvider):
    """Provider for Deepseek models (OpenAI-compatible API)."""

    MODELS = {
        "deepseek-chat": "deepseek-chat",
        "deepseek-coder": "deepseek-coder",
        "deepseek-reasoner": "deepseek-reasoner",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Deepseek provider.

        Args:
            api_key: Deepseek API key. Uses DEEPSEEK_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self._client = None

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def default_model(self) -> str:
        return "deepseek-chat"

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1",
            )
        return self._client

    def _resolve_model(self, model: Optional[str]) -> str:
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

        response = client.chat.completions.create(
            model=resolved_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=resolved_model,
            provider=self.name,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
