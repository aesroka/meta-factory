"""Estimation contracts for PERT and Cone of Uncertainty calculations."""

from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Any, Dict, List, Optional
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
        """Ensure PERT calculations are correct; auto-fix LLM rounding errors."""
        expected = (self.optimistic_hours + 4 * self.likely_hours + self.pessimistic_hours) / 6
        std = max(0.0, (self.pessimistic_hours - self.optimistic_hours) / 6)

        if abs(self.expected_hours - expected) > 0.01:
            object.__setattr__(self, 'expected_hours', round(expected, 2))
        if abs(self.std_dev - std) > 0.01:
            object.__setattr__(self, 'std_dev', round(std, 2))
        return self


class ConeOfUncertainty(BaseModel):
    """Cone of Uncertainty multipliers based on project phase (McConnell)."""
    phase: str = Field(..., description="Project phase: initial_concept, approved_product_definition, requirements_complete, ui_design_complete, detailed_design_complete, software_complete")
    low_multiplier: float = Field(..., gt=0, description="Low end multiplier for this phase")
    high_multiplier: float = Field(..., gt=0, description="High end multiplier for this phase")
    base_estimate: float = Field(0.0, ge=0, description="Base estimate in hours (derived from range if omitted)")
    range_low: float = Field(0.0, ge=0, description="Low end of range: base * low_multiplier")
    range_high: float = Field(0.0, ge=0, description="High end of range: base * high_multiplier")

    @model_validator(mode='before')
    @classmethod
    def derive_missing_fields(cls, data: Any) -> Any:
        """Derive base_estimate, range_low, or range_high when the LLM omits them."""
        if not isinstance(data, dict):
            return data
        base = data.get('base_estimate')
        low_m = data.get('low_multiplier')
        high_m = data.get('high_multiplier')
        r_low = data.get('range_low')
        r_high = data.get('range_high')

        # Derive base_estimate from range_high / high_multiplier (or range_low / low_multiplier)
        if not base or base == 0:
            if r_high and high_m:
                data['base_estimate'] = r_high / high_m
            elif r_low and low_m:
                data['base_estimate'] = r_low / low_m

        # Derive range_low / range_high if missing
        base = data.get('base_estimate', 0)
        if (not r_low or r_low == 0) and base and low_m:
            data['range_low'] = base * low_m
        if (not r_high or r_high == 0) and base and high_m:
            data['range_high'] = base * high_m

        return data

    @model_validator(mode='after')
    def validate_range_calculations(self) -> 'ConeOfUncertainty':
        """Ensure range calculations are correct; auto-fix LLM rounding errors."""
        expected_low = self.base_estimate * self.low_multiplier
        expected_high = self.base_estimate * self.high_multiplier

        if abs(self.range_low - expected_low) > 0.01:
            object.__setattr__(self, 'range_low', round(expected_low, 2))
        if abs(self.range_high - expected_high) > 0.01:
            object.__setattr__(self, 'range_high', round(expected_high, 2))
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
    total_expected_hours: float = Field(0.0, ge=0)
    total_std_dev: float = Field(0.0, ge=0)
    confidence_interval_90: tuple[float, float] = Field((0.0, 0.0), description="90% confidence interval (low, high)")
    risk_factors: List[str] = Field(default_factory=list, description="Key risk factors affecting estimates")
    caveats: List[str] = Field(default_factory=list, description="Important caveats and assumptions")

    @model_validator(mode='after')
    def validate_totals(self) -> 'EstimationResult':
        """Ensure totals match sum of individual estimates; auto-fix LLM rounding errors."""
        expected_total = sum(e.expected_hours for e in self.pert_estimates)
        expected_std = math.sqrt(sum(e.std_dev ** 2 for e in self.pert_estimates))
        ci_low = max(0.0, expected_total - 1.645 * expected_std)
        ci_high = expected_total + 1.645 * expected_std

        if abs(self.total_expected_hours - expected_total) > 0.1:
            object.__setattr__(self, 'total_expected_hours', round(expected_total, 2))
        if abs(self.total_std_dev - expected_std) > 0.1:
            object.__setattr__(self, 'total_std_dev', round(expected_std, 2))
        if abs(self.confidence_interval_90[0] - ci_low) > 0.1 or abs(self.confidence_interval_90[1] - ci_high) > 0.1:
            object.__setattr__(self, 'confidence_interval_90', (round(ci_low, 2), round(ci_high, 2)))
        return self
