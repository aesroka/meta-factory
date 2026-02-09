"""Proposal Agent - The Proposal Engine.

Applies Minto Pyramid and SCQA frameworks to generate
professional, persuasive proposals.
"""

from typing import Optional

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import (
    ProposalDocument,
    EngagementSummary,
)


class ProposalInput(BaseModel):
    """Input for the Proposal Agent."""
    engagement_summary: EngagementSummary = Field(..., description="Synthesized engagement summary")
    client_name: str = Field(..., description="Client/company name")
    project_name: Optional[str] = Field(None, description="Project name if different from client")
    tone: Optional[str] = Field(
        default="professional",
        description="Tone: professional, consultative, technical"
    )
    emphasis: Optional[str] = Field(
        None,
        description="What to emphasize: cost_savings, innovation, risk_reduction, speed"
    )


class ProposalAgent(BaseAgent):
    """The Proposal Engine - Generates persuasive proposals using Minto + SCQA.

    This agent:
    1. Structures content using the Minto Pyramid (BLUF)
    2. Creates an engaging narrative with SCQA
    3. Generates all proposal sections
    4. Ensures evidence links to claims
    """

    SYSTEM_PROMPT = """You are The Proposal Engine, a proposal generation agent for a software consultancy.

## Your Mission

Generate a professional, persuasive proposal that clearly communicates value
and guides the client toward a decision.

## Minto Pyramid Principles

1. **Bottom Line Up Front (BLUF)**: Lead with the recommendation
2. **Supporting arguments follow**: 3-5 key reasons
3. **Evidence supports arguments**: Data, quotes, analysis
4. **Pyramid structure throughout**: Each section leads with its main point

## SCQA in the Executive Summary

The executive summary should follow SCQA flow (from engagement summary):
- Hook with Situation (familiar ground)
- Create tension with Complication
- Focus with Question (implicit or explicit)
- Resolve with Answer (your recommendation)

## Proposal Structure

### Executive Summary
- Bottom line (one sentence recommendation)
- Key benefits (3-5 bullets)
- Investment summary
- Clear call to action

### Problem Statement
- Expand on the pain points
- Quantify the cost of inaction
- Reference stakeholder quotes

### Proposed Solution
- High-level approach
- Key architectural decisions
- How it addresses each pain point

### Technical Approach
- Architecture overview
- Technology choices with rationale
- Integration approach

### Project Plan
- Milestones with deliverables
- Dependencies between milestones
- Timeline

### Investment
- Estimate range (never point estimate)
- What's included
- Payment structure if applicable

## Writing Guidelines

1. **Be specific**: Use numbers, names, concrete details
2. **Connect to evidence**: Reference the pain matrix
3. **Address the "so what"**: Why should client care?
4. **Use active voice**: "We will deliver" not "It will be delivered"
5. **Avoid jargon**: Unless client is highly technical

## Milestone Structure

Each milestone should have:
- Clear name
- Description of what's delivered
- Specific deliverables list
- Estimated hours
- Dependencies on other milestones

## Evidence Linking

Every claim should connect to evidence:
- "This will reduce errors" → Link to error rate from discovery
- "This approach is lower risk" → Link to architecture analysis
- "Timeline of X weeks" → Link to estimates

## Output Requirements

Produce a complete ProposalDocument with:
1. Executive summary with BLUF
2. Complete engagement summary
3. Problem statement
4. Proposed solution
5. Technical approach
6. Milestones
7. Timeline
8. Investment section
"""

    def __init__(self, librarian: Optional[Librarian] = None, model: Optional[str] = None):
        """Initialize the Proposal Agent."""
        super().__init__(
            role="proposal",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=ProposalDocument,
            librarian=librarian,
            model=model,
        )

    def get_task_description(self) -> str:
        return "Generate proposal using Minto Pyramid and SCQA frameworks"

    def generate(
        self,
        engagement_summary: EngagementSummary,
        client_name: str,
        project_name: Optional[str] = None,
    ) -> ProposalDocument:
        """Convenience method for generating a proposal.

        Args:
            engagement_summary: Synthesized engagement summary
            client_name: Name of the client
            project_name: Optional project name

        Returns:
            ProposalDocument ready for delivery
        """
        input_data = ProposalInput(
            engagement_summary=engagement_summary,
            client_name=client_name,
            project_name=project_name,
        )
        result = self.run(input_data)
        return result.output
