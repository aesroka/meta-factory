"""Architecture contracts for system design decisions."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class ImportanceLevel(str, Enum):
    """Importance level for quality scenarios."""
    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"


class DifficultyLevel(str, Enum):
    """Difficulty level for quality scenarios."""
    HIGH = "H"
    MEDIUM = "M"
    LOW = "L"


class QualityScenario(BaseModel):
    """A quality attribute scenario for ATAM analysis."""
    attribute: str = Field(..., description="Quality attribute: performance, security, scalability, etc.")
    scenario: str = Field(..., description="Specific scenario description")
    importance: ImportanceLevel = Field(..., description="Business importance")
    difficulty: DifficultyLevel = Field(..., description="Technical difficulty to achieve")
    stimulus: Optional[str] = Field(None, description="What triggers this scenario")
    response: Optional[str] = Field(None, description="Expected system response")
    response_measure: Optional[str] = Field(None, description="How to measure the response")


class UtilityTree(BaseModel):
    """Utility tree for prioritising quality attributes (ATAM)."""
    scenarios: List[QualityScenario] = Field(..., min_length=1)

    def get_high_priority_scenarios(self) -> List[QualityScenario]:
        """Return scenarios that are both high importance and high difficulty."""
        return [s for s in self.scenarios
                if s.importance == ImportanceLevel.HIGH and s.difficulty == DifficultyLevel.HIGH]


class FailureMode(BaseModel):
    """A potential failure mode for an architecture decision."""
    description: str = Field(..., description="What could go wrong")
    likelihood: str = Field(..., description="How likely: rare, possible, likely")
    impact: str = Field(..., description="Impact if it occurs: minor, moderate, severe")
    mitigation: str = Field(..., description="How to mitigate or detect this failure")


class ArchitectureDecision(BaseModel):
    """A significant architecture decision with rationale."""
    decision: str = Field(..., description="The decision made")
    context: str = Field(..., description="Context and constraints that led to this decision")
    pattern_used: str = Field(..., description="Architecture/design pattern applied")
    eip_reference: Optional[str] = Field(None, description="Enterprise Integration Pattern reference if applicable")
    trade_off: str = Field(..., description="What trade-offs this decision involves")
    alternatives_considered: List[str] = Field(default_factory=list, description="Other options that were considered")
    failure_modes: List[FailureMode] = Field(default_factory=list, description="Potential failure modes")


class TradeOffMatrix(BaseModel):
    """Matrix comparing trade-offs between different architectural approaches."""
    options: List[str] = Field(..., description="Options being compared")
    criteria: List[str] = Field(..., description="Criteria for comparison")
    scores: List[List[int]] = Field(..., description="Scores matrix: options x criteria (1-5)")
    recommendation: str = Field(..., description="Recommended option with rationale")


class ArchitectureResult(BaseModel):
    """Complete output from Architecture Agent."""
    utility_tree: UtilityTree = Field(...)
    decisions: List[ArchitectureDecision] = Field(..., min_length=1)
    trade_off_analysis: Optional[TradeOffMatrix] = Field(None)
    integration_patterns: List[str] = Field(default_factory=list, description="EIP patterns used")
    component_diagram: Optional[str] = Field(None, description="Mermaid/PlantUML diagram code")
