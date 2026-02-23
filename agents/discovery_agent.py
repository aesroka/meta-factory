"""Discovery Agent - The Inquisitor.

Applies Mom Test + SPIN Selling frameworks to extract validated pain points
and stakeholder needs from transcripts and input materials.
"""

from typing import Optional

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import PainMonetizationMatrix


class DiscoveryInput(BaseModel):
    """Input for the Discovery Agent."""
    transcript: str = Field(..., description="Meeting transcript or raw input text")
    context: Optional[str] = Field(None, description="Additional context about the client/project")
    focus_areas: Optional[list[str]] = Field(None, description="Specific areas to focus on")


class DiscoveryAgent(BaseAgent):
    """The Inquisitor - Extracts and validates pain points using Mom Test + SPIN.

    This agent analyzes transcripts and input materials to:
    1. Identify pain points grounded in past behavior (Mom Test)
    2. Quantify the impact using SPIN methodology
    3. Map stakeholder needs by role
    4. Produce a Pain-Monetization Matrix

    System prompt is loaded from agents/prompts/discovery.yaml (use --prompt-variant to select variant).
    """

    DEFAULT_TIER = "tier1"

    def __init__(
        self,
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        prompt_variant: str = "default",
    ):
        """Initialize the Discovery Agent. Prompt loaded from agents/prompts/discovery.yaml."""
        super().__init__(
            role="discovery",
            output_schema=PainMonetizationMatrix,
            librarian=librarian,
            model=model,
            provider=provider,
            prompt_variant=prompt_variant,
        )

    def get_task_description(self) -> str:
        return "Extract and validate pain points using Mom Test + SPIN methodology"

    def analyze(self, transcript: str, context: Optional[str] = None) -> PainMonetizationMatrix:
        """Convenience method for running discovery analysis.

        Args:
            transcript: The transcript or input text to analyze
            context: Optional additional context

        Returns:
            PainMonetizationMatrix with validated pain points
        """
        input_data = DiscoveryInput(transcript=transcript, context=context)
        result = self.run(input_data)
        return result.output
