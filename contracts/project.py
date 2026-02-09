"""Project Dossier contracts for Forge-Stream.

The compressed source of truth produced by Tier 1 Miners and consumed by Tier 3 Experts.
All cross-tier data must validate against these models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Stakeholder(BaseModel):
    """Stakeholder extracted from project materials."""

    name: str
    role: str
    concerns: List[str]


class TechConstraint(BaseModel):
    """Technical constraint or requirement."""

    category: str = Field(description="e.g., Database, Frontend, Security")
    requirement: str
    priority: str = Field(
        description="Must-have, Should-have, Nice-to-have"
    )


class CoreLogicFlow(BaseModel):
    """A core business or technical flow."""

    trigger: str
    process: str
    outcome: str


class ProjectDossier(BaseModel):
    """The compressed source of truth produced by Tier 1 Miners.

    Serves as the unified knowledge bridge between Miner agents and Expert agents.
    """

    project_name: str
    summary: str = Field(
        description="High-level 2-paragraph summary of the project goals."
    )
    stakeholders: List[Stakeholder]
    tech_stack_detected: List[str]
    constraints: List[TechConstraint]
    logic_flows: List[CoreLogicFlow]
    legacy_debt_summary: Optional[str] = Field(
        default=None,
        description="Only for Brownfield/Greyfield modes.",
    )
