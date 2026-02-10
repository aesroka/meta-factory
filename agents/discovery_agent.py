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
    """

    SYSTEM_PROMPT = """You are The Inquisitor, a discovery analysis agent for a software consultancy.

## Your Mission

Analyze the provided transcript/input to extract a validated Pain-Monetization Matrix.
Your analysis must be grounded in EVIDENCE, not assumptions.

## Key Principles (from Mom Test)

1. Only extract pain points that have EVIDENCE in the input
2. Look for PAST BEHAVIOR, not future intentions
3. Identify CONCRETE incidents, not hypotheticals
4. Find QUANTIFIABLE impact wherever possible
5. Capture DIRECT QUOTES that evidence each pain point

## Using SPIN Framework

For each pain point identified:
- **Situation**: What's the current state?
- **Problem**: What specific difficulty exists?
- **Implication**: What are the consequences? (This creates urgency)
- **Need-Payoff**: What would solving this enable? (If stated by stakeholder)

## Output Requirements

1. **Pain Points**: Each must have:
   - Clear description of the problem
   - Frequency (how often it occurs)
   - Cost per incident (if quantifiable from input)
   - Annual cost (calculated or stated)
   - Source quote from the input (MANDATORY)
   - Your confidence level (0-1)

2. **Stakeholder Needs**: Map needs to specific roles

3. **Constraints**: Identify any hard constraints mentioned

4. **Next Steps**: Recommend logical follow-up questions/actions

## Critical Rules

- DO NOT invent pain points not evidenced in the input
- DO NOT guess at costs - only include if you can derive from input
- DO NOT include hypothetical benefits not grounded in evidence
- Every pain point MUST have a source_quote from the actual input
- If the input lacks concrete evidence, lower your confidence scores
"""

    def __init__(
        self,
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Initialize the Discovery Agent."""
        super().__init__(
            role="discovery",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=PainMonetizationMatrix,
            librarian=librarian,
            model=model,
            provider=provider,
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
