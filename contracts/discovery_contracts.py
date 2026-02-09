"""Discovery contracts for pain point analysis and stakeholder mapping."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class Frequency(str, Enum):
    """How often a pain point occurs."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    RARELY = "rarely"


class Priority(str, Enum):
    """Priority level for stakeholder needs."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PainPoint(BaseModel):
    """A single validated pain point extracted from discovery."""
    description: str = Field(..., description="What the pain point is")
    frequency: Frequency = Field(..., description="How often this occurs")
    cost_per_incident: Optional[float] = Field(None, description="Estimated $ cost per occurrence")
    annual_cost: Optional[float] = Field(None, description="Annualised cost impact")
    source_quote: str = Field(..., description="Direct quote from transcript/input that evidences this")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Agent confidence in this pain point")


class StakeholderNeed(BaseModel):
    """A need expressed by a specific stakeholder role."""
    role: str = Field(..., description="e.g., 'CTO', 'Operations Manager', 'End User'")
    need: str = Field(..., description="The specific need expressed")
    priority: Priority = Field(..., description="Priority level of this need")


class PainMonetizationMatrix(BaseModel):
    """The primary output of the Discovery Agent. Input for Architecture + Proposal."""
    pain_points: List[PainPoint] = Field(..., min_length=1)
    stakeholder_needs: List[StakeholderNeed] = Field(default_factory=list)
    total_annual_cost_of_pain: Optional[float] = Field(None, description="Sum of quantified pain")
    key_constraints: List[str] = Field(default_factory=list, description="Hard constraints identified: regulatory, technical, budgetary")
    recommended_next_steps: List[str] = Field(default_factory=list)
