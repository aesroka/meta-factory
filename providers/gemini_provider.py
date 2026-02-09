"""Google Gemini provider implementation."""

import os
from typing import Optional

from .base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Provider for Google Gemini models."""

    MODELS = {
        "gemini-2.0-flash": "gemini-2.0-flash-exp",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini-1.5-flash": "gemini-1.5-flash",
        "gemini-pro": "gemini-1.5-pro",
        "gemini-flash": "gemini-1.5-flash",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider.

        Args:
            api_key: Google API key. Uses GOOGLE_API_KEY or GEMINI_API_KEY env var if not provided.
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self._configured = False

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-1.5-pro"

    def _configure(self):
        if not self._configured and self.api_key:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._configured = True

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
        import google.generativeai as genai

        self._configure()
        resolved_model = self._resolve_model(model)

        # Gemini uses a different API structure
        gen_model = genai.GenerativeModel(
            model_name=resolved_model,
            system_instruction=system_prompt,
        )

        response = gen_model.generate_content(
            user_message,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
            ),
        )

        # Gemini doesn't always provide token counts in the same way
        # We estimate if not available
        input_tokens = getattr(response.usage_metadata, 'prompt_token_count', len(system_prompt + user_message) // 4)
        output_tokens = getattr(response.usage_metadata, 'candidates_token_count', len(response.text) // 4)

        return LLMResponse(
            content=response.text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=resolved_model,
            provider=self.name,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
