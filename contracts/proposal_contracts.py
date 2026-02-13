"""Proposal contracts for final deliverable generation."""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from .discovery_contracts import PainMonetizationMatrix
from .architecture_contracts import ArchitectureDecision
from .estimation_contracts import PERTEstimate, ConeOfUncertainty


class SCQAFrame(BaseModel):
    """Minto Pyramid SCQA framework for structuring communication."""
    situation: str = Field(..., description="The current state - what the audience already knows and agrees with")
    complication: str = Field(..., description="What has changed or gone wrong that creates tension")
    question: str = Field(..., description="The question that naturally arises from the complication")
    answer: str = Field(..., description="The answer/recommendation - the key message")


class ExecutiveSummary(BaseModel):
    """Executive summary following BLUF (Bottom Line Up Front) principle."""
    bottom_line: str = Field(..., description="The single most important takeaway")
    key_benefits: List[str] = Field(..., min_length=1, max_length=5, description="Top 3-5 benefits")
    investment_summary: str = Field(..., description="High-level investment required")
    recommended_action: str = Field(..., description="Clear call to action")


class Milestone(BaseModel):
    """A project milestone."""
    name: str = Field(...)
    description: str = Field(...)
    deliverables: List[str] = Field(...)
    estimated_hours: float = Field(..., ge=0)
    dependencies: List[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    """A project risk with mitigation."""
    risk: str = Field(...)
    probability: str = Field(..., description="low, medium, high")
    impact: str = Field(..., description="low, medium, high")
    mitigation: str = Field(...)


class DeliveryPhase(BaseModel):
    """A distinct release phase with its own value proposition (Phase 9)."""
    phase_name: str = Field(..., description="e.g. 'POC', 'MVP', 'V1', 'V1.1 – Analytics Extension'")
    phase_type: str = Field(..., description="poc, mvp, v1, extension")
    goal: str = Field(..., description="What this phase proves or delivers — one sentence")
    success_criteria: List[str] = Field(..., min_length=1, description="How we know this phase is done")
    milestones: List[Milestone] = Field(..., min_length=1)
    estimated_hours: float = Field(..., ge=0, description="PERT expected hours for this phase")
    estimated_weeks: int = Field(..., ge=1)
    estimated_cost_gbp: Optional[float] = Field(None, description="Cost at the given hourly rate")
    can_stop_here: bool = Field(..., description="True if the client gets standalone value from just this phase")
    prerequisites: List[str] = Field(default_factory=list, description="Which prior phases must complete first")


class EngagementSummary(BaseModel):
    """Complete engagement summary merging all upstream artifacts."""
    scqa: SCQAFrame = Field(...)
    pain_matrix: PainMonetizationMatrix = Field(...)
    architecture_decisions: List[ArchitectureDecision] = Field(...)
    estimates: List[PERTEstimate] = Field(...)
    total_estimate: ConeOfUncertainty = Field(...)
    key_risks: List[RiskItem] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    out_of_scope: List[str] = Field(default_factory=list)


class ProposalDocument(BaseModel):
    """The final proposal document."""
    title: str = Field(...)
    client_name: str = Field(...)
    prepared_by: str = Field(default="Meta-Factory AI")
    date: datetime = Field(default_factory=datetime.now)

    executive_summary: ExecutiveSummary = Field(...)
    engagement_summary: EngagementSummary = Field(...)

    # Detailed sections
    problem_statement: str = Field(..., description="Detailed problem analysis")
    proposed_solution: str = Field(..., description="Detailed solution description")
    technical_approach: str = Field(..., description="Technical approach and architecture")

    milestones: List[Milestone] = Field(...)
    timeline_weeks: int = Field(..., ge=1)

    delivery_phases: List[DeliveryPhase] = Field(
        default_factory=list,
        description="POC → MVP → V1 → Extensions. Each phase delivers standalone value.",
    )
    recommended_first_phase: Optional[str] = Field(None, description="Which phase to start with — usually POC or MVP")
    total_estimated_hours: Optional[float] = Field(None, ge=0)
    total_estimated_weeks: Optional[int] = Field(None, ge=1)

    investment: str = Field(..., description="Investment/pricing section")
    terms_and_conditions: Optional[str] = Field(None)

    appendices: List[str] = Field(default_factory=list, description="References to detailed appendix documents")

    def to_markdown(self) -> str:
        """Convert proposal to markdown format."""
        sections = [
            f"# {self.title}",
            f"\n**Prepared for:** {self.client_name}",
            f"**Prepared by:** {self.prepared_by}",
            f"**Date:** {self.date.strftime('%Y-%m-%d')}",
            "\n---\n",
            "## Executive Summary",
            f"\n**{self.executive_summary.bottom_line}**\n",
            "### Key Benefits",
            *[f"- {b}" for b in self.executive_summary.key_benefits],
            f"\n**Investment:** {self.executive_summary.investment_summary}",
            f"\n**Recommended Action:** {self.executive_summary.recommended_action}",
            "\n---\n",
            "## Problem Statement",
            self.problem_statement,
            "\n## Proposed Solution",
            self.proposed_solution,
            "\n## Technical Approach",
            self.technical_approach,
            "\n## Project Milestones",
            *[f"### {m.name}\n{m.description}\n\n**Deliverables:**\n" + "\n".join(f"- {d}" for d in m.deliverables) for m in self.milestones],
            f"\n## Timeline\n\nEstimated duration: **{self.timeline_weeks} weeks**",
            f"\n## Investment\n\n{self.investment}",
        ]
        return "\n".join(sections)
