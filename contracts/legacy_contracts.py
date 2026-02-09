"""Legacy contracts for brownfield codebase analysis."""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class SeamType(str, Enum):
    """Type of seam identified in legacy code (from Feathers)."""
    OBJECT = "object"
    LINK = "link"
    PREPROCESSOR = "preprocessor"


class RiskLevel(str, Enum):
    """Risk level for modifications."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RemediationStrategy(str, Enum):
    """Strategy for addressing technical debt (from Feathers)."""
    SPROUT = "sprout"  # Sprout method/class
    WRAP = "wrap"  # Wrap and delegate
    EXTRACT = "extract"  # Extract and override


class C4Level(str, Enum):
    """C4 model diagram levels."""
    CONTEXT = "context"
    CONTAINER = "container"
    COMPONENT = "component"
    CODE = "code"


class SeamAnalysis(BaseModel):
    """Analysis of a seam in legacy code where changes can be safely introduced."""
    seam_type: SeamType = Field(..., description="Type of seam identified")
    location: str = Field(..., description="File/module/class location of the seam")
    risk_level: RiskLevel = Field(..., description="Risk level of modifying at this seam")
    test_strategy: str = Field(..., description="Recommended testing approach for this seam")
    description: str = Field(..., description="Description of the seam and why it's suitable")


class TechDebtItem(BaseModel):
    """A single technical debt item identified in the codebase."""
    module: str = Field(..., description="Module or file containing the debt")
    debt_type: str = Field(..., description="Type of debt: coupling, complexity, duplication, etc.")
    cyclomatic_complexity: Optional[int] = Field(None, description="Cyclomatic complexity if applicable")
    coupling_description: str = Field(..., description="Description of coupling issues")
    remediation_strategy: RemediationStrategy = Field(..., description="Recommended remediation approach")
    estimated_effort_hours: float = Field(..., ge=0, description="Estimated hours to remediate")


class C4Diagram(BaseModel):
    """A C4 model diagram representation."""
    level: C4Level = Field(..., description="Which C4 level this diagram represents")
    title: str = Field(..., description="Title of the diagram")
    elements: List[str] = Field(..., description="Key elements/components in the diagram")
    relationships: List[str] = Field(..., description="Key relationships between elements")
    diagram_code: Optional[str] = Field(None, description="PlantUML or Mermaid code for the diagram")


class ConstraintList(BaseModel):
    """Constraints identified from legacy analysis."""
    hard_constraints: List[str] = Field(default_factory=list, description="Non-negotiable constraints")
    soft_constraints: List[str] = Field(default_factory=list, description="Preferred but flexible constraints")
    no_go_zones: List[str] = Field(default_factory=list, description="Areas that must not be modified")


class LegacyAnalysisResult(BaseModel):
    """Complete output from Legacy Agent analysis."""
    seams: List[SeamAnalysis] = Field(default_factory=list)
    tech_debt: List[TechDebtItem] = Field(default_factory=list)
    c4_diagrams: List[C4Diagram] = Field(default_factory=list)
    constraints: ConstraintList = Field(default_factory=ConstraintList)
    summary: str = Field(..., description="Executive summary of legacy analysis")
