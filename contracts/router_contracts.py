"""Router contracts for input classification and routing decisions."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum


class InputType(str, Enum):
    """Type of input received by the system."""
    CODE_BASE = "code_base"
    TRANSCRIPT = "transcript"
    IDEA = "idea"
    HYBRID = "hybrid"


class Mode(str, Enum):
    """Operating mode for the factory."""
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"
    GREYFIELD = "greyfield"


class InputClassification(BaseModel):
    """Classification result for input analysis."""
    input_type: InputType = Field(..., description="Detected type of input")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in classification")
    evidence: str = Field(..., description="Evidence supporting this classification")
    recommended_mode: Mode = Field(..., description="Recommended processing mode")


class RoutingDecision(BaseModel):
    """Decision on how to route the input through the system."""
    mode: Mode = Field(..., description="Selected operating mode")
    swarm_config: Dict[str, Any] = Field(default_factory=dict, description="Configuration for the selected swarm")
    bibles_to_load: List[str] = Field(..., description="List of Bible/framework cheat sheets to load")
