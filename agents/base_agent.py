"""Base agent class that all specialized agents inherit from.

Every agent:
- Loads Bible context from Librarian
- Calls LLM with system prompt + Bible context + task input
- Validates output against expected Pydantic contract
- Tracks token usage for cost controller
"""

import json
from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel, ValidationError

from librarian import Librarian
from providers import get_provider, LLMProvider
from config import settings

T = TypeVar("T", bound=BaseModel)


class TokenUsage(BaseModel):
    """Track token usage for cost calculation."""
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_cost(self) -> float:
        """Calculate cost based on current token pricing."""
        return settings.calculate_cost(self.input_tokens, self.output_tokens)


class AgentResult(BaseModel):
    """Result from an agent run, including output and metadata."""
    output: Any
    token_usage: TokenUsage
    model: str
    provider: str = "anthropic"
    raw_response: Optional[str] = None
    retries: int = 0


class BaseAgent(ABC):
    """Base class for all Meta-Factory agents.

    Responsibilities:
    - Loads Bible context from Librarian
    - Calls LLM with system prompt + Bible context + task input
    - Validates output against the expected Pydantic contract
    - Tracks token usage for cost controller

    Supports multiple LLM providers: Anthropic, OpenAI, Gemini, Deepseek
    """

    def __init__(
        self,
        role: str,
        system_prompt: str,
        output_schema: Type[T],
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        depth: Optional[str] = None,
    ):
        """Initialize the agent.

        Args:
            role: Agent role for Bible loading (e.g., 'discovery', 'architect')
            system_prompt: The agent's system prompt defining its behavior
            output_schema: Pydantic model class for validating output
            librarian: Librarian instance for loading Bible context
            model: Override the default model (e.g., 'gpt-4o', 'gemini-pro', 'deepseek-chat')
            provider: Explicit provider name (anthropic, openai, gemini, deepseek)
                     If not specified, auto-detected from model name or defaults to anthropic
            depth: Bible context depth — "cheat_sheet" (default for tier1/tier2) or "full" (tier0/tier3).
                   If None, derived from DEFAULT_TIER.
        """
        self.role = role
        self.system_prompt = system_prompt
        self.output_schema = output_schema
        self.model = model

        self.librarian = librarian or Librarian()
        default_tier = getattr(self.__class__, "DEFAULT_TIER", None)
        self._context_depth = depth if depth is not None else (
            "full" if default_tier in ("tier0", "tier3") else "cheat_sheet"
        )
        self.bible_context = self._load_bible_context()

        # Get the LLM provider (when model is None, we may use DEFAULT_TIER for routing)
        self.llm_provider: LLMProvider = get_provider(provider_name=provider, model=model)
        self.model = model or getattr(self.__class__, "DEFAULT_TIER", None) or self.llm_provider.default_model
        if hasattr(self.llm_provider, "set_metadata"):
            tier = getattr(self.__class__, "DEFAULT_TIER", "?")
            self.llm_provider.set_metadata({"agent": self.role, "tier": tier})

        self.total_usage = TokenUsage()

    def _load_bible_context(self) -> str:
        """Load Bible context for this agent's role (depth: cheat_sheet or full)."""
        try:
            return self.librarian.get_context_for_agent(self.role, depth=getattr(self, "_context_depth", "cheat_sheet"))
        except ValueError:
            # Role not in mapping, return empty context
            return ""

    def _build_full_system_prompt(self) -> str:
        """Build the complete system prompt including Bible context."""
        parts = [self.system_prompt]

        if self.bible_context:
            parts.append("\n\n# FRAMEWORK KNOWLEDGE\n")
            parts.append("Use the following frameworks to guide your analysis:\n\n")
            parts.append(self.bible_context)

        parts.append("\n\n# OUTPUT FORMAT\n")
        parts.append(f"You MUST respond with valid JSON matching this schema:\n\n")
        parts.append(f"```json\n{json.dumps(self.output_schema.model_json_schema(), indent=2)}\n```")

        return "".join(parts)

    def _parse_and_validate(self, response_text: str) -> T:
        """Parse LLM response and validate against schema.

        Args:
            response_text: Raw text response from LLM

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If response doesn't match schema
            json.JSONDecodeError: If response isn't valid JSON
        """
        # Try to extract JSON from the response
        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        # Parse JSON
        data = json.loads(text)

        # Validate against schema
        return self.output_schema.model_validate(data)

    def run(
        self,
        input_data: BaseModel,
        max_retries: int = 1,
        model: Optional[str] = None,
    ) -> AgentResult:
        """Execute the agent.

        Args:
            input_data: Input data as a Pydantic model
            max_retries: Number of retries on validation failure
            model: Optional model override for this call (e.g. "tier3" for escalation).
                   If None, uses self.model set at init.

        Returns:
            AgentResult with validated output and metadata

        Raises:
            ValidationError: If output validation fails after retries
            Exception: If LLM call fails
        """
        full_system_prompt = self._build_full_system_prompt()
        user_message = f"# INPUT\n\n{input_data.model_dump_json(indent=2)}"

        last_error = None
        retries = 0

        for attempt in range(max_retries + 1):
            try:
                # Add error context on retry
                if attempt > 0 and last_error:
                    user_message = (
                        f"# INPUT\n\n{input_data.model_dump_json(indent=2)}\n\n"
                        f"# PREVIOUS ERROR\n\n"
                        f"Your previous response did not match the required schema. "
                        f"Error: {last_error}\n\n"
                        f"Please fix the issues and provide a valid JSON response."
                    )
                    retries = attempt

                # Call the LLM via provider (model override for this call, e.g. tier escalation)
                response = self.llm_provider.complete(
                    system_prompt=full_system_prompt,
                    user_message=user_message,
                    model=model or self.model,
                    max_tokens=settings.max_tokens_per_agent_call,
                )

                # Track token usage
                usage = TokenUsage(
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                )
                self.total_usage.input_tokens += usage.input_tokens
                self.total_usage.output_tokens += usage.output_tokens

                # Parse and validate
                output = self._parse_and_validate(response.content)

                return AgentResult(
                    output=output,
                    token_usage=usage,
                    model=response.model,
                    provider=response.provider,
                    raw_response=response.content,
                    retries=retries,
                )

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)
                if attempt == max_retries:
                    raise

        # Should not reach here
        raise RuntimeError("Unexpected error in agent run loop")

    @abstractmethod
    def get_task_description(self) -> str:
        """Return a description of what this agent does.

        Used for logging and debugging.
        """
        pass


class AgentInput(BaseModel):
    """Generic input wrapper for agents."""
    content: str
    context: Optional[Dict[str, Any]] = None
    previous_artifacts: Optional[Dict[str, Any]] = None
