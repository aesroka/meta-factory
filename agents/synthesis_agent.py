"""Synthesis Agent - The Synthesizer.

Merges all upstream artifacts into a coherent EngagementSummary
that serves as input for the Proposal Agent.
"""

from typing import Optional, List

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import (
    EngagementSummary,
    PainMonetizationMatrix,
    ArchitectureResult,
    EstimationResult,
    LegacyAnalysisResult,
    SCQAFrame,
    RiskItem,
)


class SynthesisInput(BaseModel):
    """Input for the Synthesis Agent."""
    pain_matrix: PainMonetizationMatrix = Field(..., description="Discovery output")
    architecture_result: ArchitectureResult = Field(..., description="Architecture output")
    estimation_result: EstimationResult = Field(..., description="Estimation output")
    legacy_analysis: Optional[LegacyAnalysisResult] = Field(
        None,
        description="Legacy analysis if brownfield/greyfield"
    )
    client_name: Optional[str] = Field(None, description="Client name for context")
    project_name: Optional[str] = Field(None, description="Project name for context")


class SynthesisAgent(BaseAgent):
    """The Synthesizer - Merges upstream artifacts into coherent summary.

    This agent:
    1. Creates an SCQA frame from the discovery findings
    2. Synthesizes key risks from all sources
    3. Identifies assumptions and out-of-scope items
    4. Produces a complete EngagementSummary
    """

    SYSTEM_PROMPT = """You are The Synthesizer, an integration agent for a software consultancy.

## Your Mission

Merge all upstream artifacts (discovery, architecture, estimation, legacy analysis)
into a coherent EngagementSummary that tells a complete story.

## SCQA Frame Creation

Create a compelling SCQA frame:
- **Situation**: The current state (from pain matrix)
- **Complication**: What's broken/changing (key pain points)
- **Question**: The strategic question this raises
- **Answer**: The proposed solution (from architecture)

The SCQA should flow naturally and create engagement.

## Risk Synthesis

Identify key risks from all sources:
- Discovery: Stakeholder alignment, scope creep, requirement volatility
- Architecture: Technical risks, integration risks, scaling risks
- Estimation: Schedule risks, resource risks, dependency risks
- Legacy: Technical debt risks, compatibility risks, data migration risks

For each risk, provide:
- Description of the risk
- Probability (low/medium/high)
- Impact (low/medium/high)
- Mitigation strategy

## Assumptions

Gather assumptions from all sources:
- Technical assumptions (architecture works as designed)
- Business assumptions (stakeholders available, decisions timely)
- Resource assumptions (team composition, availability)
- External assumptions (third-party dependencies, APIs)

## Out of Scope

Explicitly identify what is NOT included:
- Features mentioned but deprioritized
- Technical capabilities not addressed
- Future phases mentioned but not estimated

## Coherence Check

Ensure:
1. Pain points in matrix are addressed by architecture decisions
2. Architecture decisions are reflected in estimates
3. Risks are mitigated by proposed approach
4. Assumptions are realistic and stated

## Output Requirements

Produce a complete EngagementSummary with:
1. SCQA frame that tells the story
2. Complete pain matrix (passed through)
3. Architecture decisions (passed through)
4. Estimates (passed through)
5. Total estimate with Cone of Uncertainty
6. Synthesized risks
7. Consolidated assumptions
8. Clear out-of-scope items
"""

    def __init__(
        self,
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Initialize the Synthesis Agent."""
        super().__init__(
            role="proposal",  # Uses Minto/SCQA frameworks
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=EngagementSummary,
            librarian=librarian,
            model=model,
            provider=provider,
        )

    def get_task_description(self) -> str:
        return "Synthesize all artifacts into coherent engagement summary"

    def synthesize(
        self,
        pain_matrix: PainMonetizationMatrix,
        architecture_result: ArchitectureResult,
        estimation_result: EstimationResult,
        legacy_analysis: Optional[LegacyAnalysisResult] = None,
    ) -> EngagementSummary:
        """Convenience method for running synthesis.

        Args:
            pain_matrix: Discovery output
            architecture_result: Architecture output
            estimation_result: Estimation output
            legacy_analysis: Optional legacy analysis

        Returns:
            EngagementSummary ready for proposal generation
        """
        input_data = SynthesisInput(
            pain_matrix=pain_matrix,
            architecture_result=architecture_result,
            estimation_result=estimation_result,
            legacy_analysis=legacy_analysis,
        )
        result = self.run(input_data)
        return result.output
