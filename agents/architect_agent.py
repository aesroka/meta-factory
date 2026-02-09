"""Architect Agent - The Architect.

Applies EIP patterns and ATAM methodology to design solutions
that address quality attributes with explicit trade-off analysis.
"""

from typing import Optional, List

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import (
    ArchitectureResult,
    PainMonetizationMatrix,
    ConstraintList,
)


class ArchitectInput(BaseModel):
    """Input for the Architect Agent."""
    pain_matrix: PainMonetizationMatrix = Field(..., description="Pain points and stakeholder needs")
    constraints: Optional[ConstraintList] = Field(None, description="Constraints from legacy analysis")
    quality_priorities: Optional[List[str]] = Field(
        None,
        description="Priority quality attributes (performance, security, etc.)"
    )
    technology_preferences: Optional[List[str]] = Field(
        None,
        description="Preferred or required technologies"
    )
    integration_requirements: Optional[List[str]] = Field(
        None,
        description="Systems that must be integrated with"
    )


class ArchitectAgent(BaseAgent):
    """The Architect - Designs solutions using EIP + ATAM.

    This agent:
    1. Builds a utility tree of quality attribute scenarios
    2. Makes architecture decisions with explicit trade-offs
    3. Applies Enterprise Integration Patterns where appropriate
    4. Identifies failure modes and mitigations
    """

    SYSTEM_PROMPT = """You are The Architect, a solution design agent for a software consultancy.

## Your Mission

Design a software architecture that addresses the identified pain points while meeting
quality attribute requirements. Every decision must have explicit trade-off analysis.

## ATAM Methodology

1. **Build a Utility Tree**:
   - Identify key quality attributes (performance, security, scalability, etc.)
   - Create specific scenarios for each attribute
   - Rate each scenario: Importance (H/M/L) × Difficulty (H/M/L)
   - Focus on (H,H) scenarios - these are architecture drivers

2. **For Each Architecture Decision**:
   - State the decision clearly
   - Explain the context and constraints
   - Identify the pattern being used
   - Explicitly state trade-offs
   - List potential failure modes with mitigations

## Enterprise Integration Patterns

When integration is needed, apply appropriate patterns:
- Message Channel for async communication
- Content-Based Router for conditional routing
- Scatter-Gather for parallel processing
- Aggregator for combining results
- Dead Letter Channel for failure handling

Always reference the specific EIP pattern being used.

## Quality Scenario Template

For each scenario:
- Source: Who/what generates the stimulus
- Stimulus: The triggering event
- Artifact: What part of system is affected
- Environment: Conditions when stimulus occurs
- Response: How system should respond
- Measure: How to verify the response

## Trade-Off Analysis

For each major decision, identify:
- What this decision IMPROVES
- What this decision DEGRADES or makes harder
- Why the trade-off is acceptable for this context

## Failure Mode Analysis

For each architectural component:
- What could go wrong?
- How likely is it?
- What's the impact?
- How do we detect/mitigate it?

## Output Requirements

Produce a complete ArchitectureResult with:
1. Utility tree with prioritized scenarios
2. Architecture decisions with rationale
3. Trade-off analysis
4. EIP patterns used (if any)
5. Optional component diagram
"""

    def __init__(self, librarian: Optional[Librarian] = None, model: Optional[str] = None):
        """Initialize the Architect Agent."""
        super().__init__(
            role="architect",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=ArchitectureResult,
            librarian=librarian,
            model=model,
        )

    def get_task_description(self) -> str:
        return "Design architecture using ATAM methodology and EIP patterns"

    def design(
        self,
        pain_matrix: PainMonetizationMatrix,
        constraints: Optional[ConstraintList] = None,
        quality_priorities: Optional[List[str]] = None,
    ) -> ArchitectureResult:
        """Convenience method for running architecture design.

        Args:
            pain_matrix: Pain points and stakeholder needs
            constraints: Optional constraints from legacy analysis
            quality_priorities: Optional priority quality attributes

        Returns:
            ArchitectureResult with utility tree, decisions, and trade-offs
        """
        input_data = ArchitectInput(
            pain_matrix=pain_matrix,
            constraints=constraints,
            quality_priorities=quality_priorities,
        )
        result = self.run(input_data)
        return result.output
