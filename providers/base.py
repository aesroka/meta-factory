"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    cost: float = 0.0


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (anthropic, openai, gemini, deepseek)."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass

    @abstractmethod
    def complete(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a completion.

        Args:
            system_prompt: System/instruction prompt
            user_message: User message/query
            model: Model to use (defaults to provider's default)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and token counts
        """
        pass

    def is_available(self) -> bool:
        """Check if this provider is available (API key set, etc.)."""
        return True
