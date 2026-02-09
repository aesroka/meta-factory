"""Critic contracts for artifact review and validation."""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    """Severity level of a critic objection."""
    BLOCKING = "blocking"  # Prevents passage, must be fixed
    MAJOR = "major"  # Requires fix but can iterate
    MINOR = "minor"  # Logged only, does not prevent passage


class Objection(BaseModel):
    """A single objection raised by the critic."""
    category: str = Field(..., description="Category of objection: completeness, accuracy, framework_compliance, etc.")
    description: str = Field(..., description="Detailed description of the objection")
    bible_reference: str = Field(..., description="Reference to the Bible/framework this violates")
    severity: Severity = Field(..., description="Severity level")
    suggested_fix: Optional[str] = Field(None, description="Suggested way to address this objection")
    artifact_path: Optional[str] = Field(None, description="JSON path to the problematic part of the artifact")


class CriticVerdict(BaseModel):
    """The verdict from a critic review."""
    passed: bool = Field(..., description="Whether the artifact passed review")
    score: float = Field(..., ge=0.0, le=1.0, description="Overall score from 0 to 1")
    objections: List[Objection] = Field(default_factory=list)
    iteration: int = Field(..., ge=0, description="Which iteration of review this is")
    max_iterations: int = Field(default=3, description="Maximum allowed iterations")
    summary: str = Field(..., description="Summary of the review")
    strengths: List[str] = Field(default_factory=list, description="What the artifact did well")

    def has_blocking_objections(self) -> bool:
        """Check if there are any blocking objections."""
        return any(o.severity == Severity.BLOCKING for o in self.objections)

    def has_major_objections(self) -> bool:
        """Check if there are any major objections."""
        return any(o.severity == Severity.MAJOR for o in self.objections)


class ReviewLog(BaseModel):
    """Log of all reviews performed on an artifact."""
    artifact_type: str = Field(..., description="Type of artifact being reviewed")
    reviews: List[CriticVerdict] = Field(default_factory=list)
    final_passed: bool = Field(default=False)
    total_iterations: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.now)


class HumanEscalation(BaseModel):
    """Escalation to human when critic loop exhausts iterations."""
    artifact: Any = Field(..., description="The artifact that couldn't pass review")
    review_log: List[Objection] = Field(..., description="All objections raised across iterations")
    reason: str = Field(..., description="Reason for escalation")
    suggested_resolution: Optional[str] = Field(None, description="AI's suggestion for human resolution")
    context: Optional[str] = Field(None, description="Additional context for the human reviewer")
