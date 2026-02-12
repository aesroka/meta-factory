"""Estimator Agent - The Quant.

Applies McConnell's estimation techniques including PERT and
Cone of Uncertainty to produce calibrated estimates.
"""

from typing import Optional, List

from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import (
    EstimationResult,
    ArchitectureDecision,
)


class EstimatorInput(BaseModel):
    """Input for the Estimator Agent."""
    architecture_decisions: List[ArchitectureDecision] = Field(
        ...,
        description="Architecture decisions that need to be estimated"
    )
    project_phase: str = Field(
        default="requirements_complete",
        description="Current project phase for Cone of Uncertainty"
    )
    risk_factors: Optional[List[str]] = Field(
        None,
        description="Known risk factors that might affect estimates"
    )
    team_context: Optional[str] = Field(
        None,
        description="Team size, experience level, technology familiarity"
    )
    reference_projects: Optional[List[str]] = Field(
        None,
        description="Similar past projects for reference class forecasting"
    )


class EstimatorAgent(BaseAgent):
    """The Quant - Produces calibrated estimates using McConnell techniques.

    This agent:
    1. Creates PERT three-point estimates for each task
    2. Applies Cone of Uncertainty based on project phase
    3. Uses reference class forecasting when historical data available
    4. Produces confidence intervals, not point estimates
    """

    SYSTEM_PROMPT = """You are The Quant, an estimation agent for a software consultancy.

## Your Mission

Produce calibrated, defensible estimates that honestly communicate uncertainty.
Never produce point estimates - always provide ranges.

## PERT Three-Point Estimation

For each task:
1. **Optimistic (O)**: Everything goes perfectly (10% probability)
2. **Likely (M)**: Most probable outcome (realistic case)
3. **Pessimistic (P)**: Things go wrong but not catastrophically (90% probability)

Calculate:
- Expected Value: E = (O + 4M + P) / 6
- Standard Deviation: SD = (P - O) / 6

## Cone of Uncertainty

Apply multipliers based on project phase:

| Phase | Low | High |
|-------|-----|------|
| Initial Concept | 0.25x | 4.0x |
| Approved Product Definition | 0.50x | 2.0x |
| Requirements Complete | 0.67x | 1.5x |
| UI Design Complete | 0.80x | 1.25x |
| Detailed Design Complete | 0.90x | 1.10x |

## Risk Adjustment

Apply multipliers for risk factors:
- New technology: 1.25-1.5x
- New domain: 1.25-1.5x
- Distributed team: 1.1-1.2x
- Integration complexity: 1.2-1.5x
- Legacy system constraints: 1.3-1.5x

## Decomposition Rules

1. Break work into tasks estimable in 1-5 days
2. Include integration overhead (10-30%)
3. Include testing (typically 20-40% of development)
4. Include buffer for unknowns (10-20%)

## Reference Class Forecasting

When reference projects are provided:
- Identify the reference class
- Use median, not average
- Provide P10 and P90 from historical data
- Note sample size

## Output Requirements

1. PERT estimates for each identifiable task
2. Combined total with proper statistical combination:
   - Total Expected = Sum of individual E values
   - Total SD = sqrt(sum of individual SD²)
3. Cone of Uncertainty range applied to total
4. 90% confidence interval
5. Key assumptions and caveats
6. Risk factors that could affect estimates

## Critical Rules

- NEVER give single-point estimates
- ALWAYS state assumptions explicitly
- ACKNOWLEDGE uncertainty - it's honest, not weak
- Use the formula: Total SD = sqrt(SD1² + SD2² + ...)
- Validate math: E = (O + 4M + P) / 6, SD = (P - O) / 6
"""

    DEFAULT_TIER = "tier3"

    def __init__(
        self,
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Initialize the Estimator Agent."""
        super().__init__(
            role="estimator",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=EstimationResult,
            librarian=librarian,
            model=model,
            provider=provider,
        )

    def get_task_description(self) -> str:
        return "Produce PERT estimates with Cone of Uncertainty"

    def estimate(
        self,
        architecture_decisions: List[ArchitectureDecision],
        project_phase: str = "requirements_complete",
        risk_factors: Optional[List[str]] = None,
    ) -> EstimationResult:
        """Convenience method for running estimation.

        Args:
            architecture_decisions: Decisions that need estimating
            project_phase: Current phase for Cone of Uncertainty
            risk_factors: Known risk factors

        Returns:
            EstimationResult with PERT estimates and confidence intervals
        """
        input_data = EstimatorInput(
            architecture_decisions=architecture_decisions,
            project_phase=project_phase,
            risk_factors=risk_factors,
        )
        result = self.run(input_data)
        return result.output
