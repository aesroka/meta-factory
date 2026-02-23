"""Project outcome data for reference class forecasting (Phase 14)."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PhaseOutcome(BaseModel):
    """Actual outcome for a single phase."""
    phase_name: str
    phase_type: str  # poc, mvp, v1, extension

    estimated_hours: float
    actual_hours: float
    accuracy_ratio: float = Field(ge=0, description="actual / estimated")

    estimated_cost_gbp: Optional[float] = None
    actual_cost_gbp: Optional[float] = None

    estimated_weeks: int
    actual_weeks: int

    completed_date: Optional[datetime] = None
    notes: str = ""


class ProjectOutcome(BaseModel):
    """Actual outcome data for a completed project."""
    run_id: str = Field(..., description="Original proposal run_id")
    client_name: str
    project_name: str

    mode: str  # greenfield, brownfield, greyfield
    quality: str  # standard, premium

    domain: str = Field(..., description="e.g., 'logistics', 'fintech', 'healthcare'")
    project_type: str = Field(..., description="e.g., 'mobile-app', 'api-integration'")
    team_size: int = Field(ge=1, description="Number of developers")

    phases: List[PhaseOutcome]
    total_estimated_hours: float
    total_actual_hours: float
    overall_accuracy_ratio: float

    proposal_generated_date: Optional[datetime] = None
    project_completed_date: Optional[datetime] = None
    lessons_learned: str = ""

    tags: List[str] = Field(default_factory=list)


class HistoricalDatabase(BaseModel):
    """Collection of completed projects for reference class forecasting."""
    projects: List[ProjectOutcome] = []

    def add_project(self, outcome: ProjectOutcome) -> None:
        self.projects.append(outcome)

    def find_similar(
        self,
        mode: str,
        domain: Optional[str] = None,
        project_type: Optional[str] = None,
        min_similarity: float = 0.7,
    ) -> List[ProjectOutcome]:
        """Find similar historical projects."""
        similar = []
        for p in self.projects:
            similarity = 0.0
            factors = 0
            if p.mode == mode:
                similarity += 1.0
                factors += 1
            if domain and p.domain == domain:
                similarity += 1.0
                factors += 1
            if project_type and p.project_type == project_type:
                similarity += 1.0
                factors += 1
            if factors > 0:
                similarity /= factors
                if similarity >= min_similarity:
                    similar.append(p)
        return similar

    def get_correction_factor(
        self, mode: str, domain: Optional[str] = None, project_type: Optional[str] = None
    ) -> float:
        """Median accuracy ratio for similar projects (e.g. 1.3 = actual was 30% over estimate)."""
        relevant = self.find_similar(mode, domain, project_type, min_similarity=0.0)
        if not relevant:
            return 1.0
        import statistics
        return statistics.median([p.overall_accuracy_ratio for p in relevant])
