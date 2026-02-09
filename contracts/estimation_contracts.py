"""Estimation contracts for PERT and Cone of Uncertainty calculations."""

from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
import math


class PERTEstimate(BaseModel):
    """PERT (Program Evaluation and Review Technique) estimate for a task."""
    task: str = Field(..., description="Task being estimated")
    optimistic_hours: float = Field(..., ge=0, description="Best-case estimate (O)")
    likely_hours: float = Field(..., ge=0, description="Most likely estimate (M)")
    pessimistic_hours: float = Field(..., ge=0, description="Worst-case estimate (P)")
    expected_hours: float = Field(..., ge=0, description="PERT expected value: (O + 4M + P) / 6")
    std_dev: float = Field(..., ge=0, description="Standard deviation: (P - O) / 6")
    assumptions: List[str] = Field(default_factory=list, description="Key assumptions for this estimate")

    @model_validator(mode='after')
    def validate_pert_math(self) -> 'PERTEstimate':
        """Validate PERT calculations are correct."""
        expected = (self.optimistic_hours + 4 * self.likely_hours + self.pessimistic_hours) / 6
        std = (self.pessimistic_hours - self.optimistic_hours) / 6

        # Allow small floating point tolerance
        if abs(self.expected_hours - expected) > 0.01:
            raise ValueError(f"expected_hours should be {expected:.2f}, got {self.expected_hours:.2f}")
        if abs(self.std_dev - std) > 0.01:
            raise ValueError(f"std_dev should be {std:.2f}, got {self.std_dev:.2f}")

        return self


class ConeOfUncertainty(BaseModel):
    """Cone of Uncertainty multipliers based on project phase (McConnell)."""
    phase: str = Field(..., description="Project phase: initial_concept, approved_product_definition, requirements_complete, ui_design_complete, detailed_design_complete, software_complete")
    low_multiplier: float = Field(..., gt=0, description="Low end multiplier for this phase")
    high_multiplier: float = Field(..., gt=0, description="High end multiplier for this phase")
    base_estimate: float = Field(..., ge=0, description="Base estimate in hours")
    range_low: float = Field(..., ge=0, description="Low end of range: base * low_multiplier")
    range_high: float = Field(..., ge=0, description="High end of range: base * high_multiplier")

    @model_validator(mode='after')
    def validate_range_calculations(self) -> 'ConeOfUncertainty':
        """Validate range calculations are correct."""
        expected_low = self.base_estimate * self.low_multiplier
        expected_high = self.base_estimate * self.high_multiplier

        if abs(self.range_low - expected_low) > 0.01:
            raise ValueError(f"range_low should be {expected_low:.2f}")
        if abs(self.range_high - expected_high) > 0.01:
            raise ValueError(f"range_high should be {expected_high:.2f}")

        return self


class ReferenceClass(BaseModel):
    """Reference class for estimation based on similar past projects."""
    class_name: str = Field(..., description="Name of the reference class")
    sample_size: int = Field(..., ge=1, description="Number of similar projects in this class")
    median_hours: float = Field(..., ge=0, description="Median hours for projects in this class")
    p10_hours: float = Field(..., ge=0, description="10th percentile (optimistic)")
    p90_hours: float = Field(..., ge=0, description="90th percentile (pessimistic)")
    similar_projects: List[str] = Field(default_factory=list, description="Names of similar projects considered")


class EstimationResult(BaseModel):
    """Complete output from Estimator Agent."""
    pert_estimates: List[PERTEstimate] = Field(..., min_length=1)
    cone_of_uncertainty: ConeOfUncertainty = Field(...)
    reference_classes: List[ReferenceClass] = Field(default_factory=list)
    total_expected_hours: float = Field(..., ge=0)
    total_std_dev: float = Field(..., ge=0)
    confidence_interval_90: tuple[float, float] = Field(..., description="90% confidence interval (low, high)")
    risk_factors: List[str] = Field(default_factory=list, description="Key risk factors affecting estimates")
    caveats: List[str] = Field(default_factory=list, description="Important caveats and assumptions")

    @model_validator(mode='after')
    def validate_totals(self) -> 'EstimationResult':
        """Validate that totals match sum of individual estimates."""
        expected_total = sum(e.expected_hours for e in self.pert_estimates)
        # Combined std dev is sqrt of sum of variances
        expected_std = math.sqrt(sum(e.std_dev ** 2 for e in self.pert_estimates))

        if abs(self.total_expected_hours - expected_total) > 0.1:
            raise ValueError(f"total_expected_hours should be {expected_total:.2f}")
        if abs(self.total_std_dev - expected_std) > 0.1:
            raise ValueError(f"total_std_dev should be {expected_std:.2f}")

        return self
