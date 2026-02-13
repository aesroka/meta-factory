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
        """Convert proposal to a human-readable markdown report."""
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
        ]

        # Delivery phases (the main human-readable plan)
        if self.delivery_phases:
            sections.append("\n---\n")
            sections.append("## Delivery Phases")
            if self.recommended_first_phase:
                sections.append(f"\n**Recommended starting phase:** {self.recommended_first_phase}\n")
            for phase in self.delivery_phases:
                stop_label = "Yes" if phase.can_stop_here else "No"
                sections.append(f"### {phase.phase_name} ({phase.phase_type.upper()})")
                sections.append(f"\n**Goal:** {phase.goal}\n")
                sections.append(f"**Estimated effort:** {phase.estimated_hours:.0f} hours / ~{phase.estimated_weeks} weeks")
                if phase.estimated_cost_gbp:
                    sections.append(f"**Estimated cost:** {phase.estimated_cost_gbp:,.0f} GBP")
                sections.append(f"**Can stop here with standalone value:** {stop_label}\n")
                if phase.prerequisites:
                    sections.append(f"**Prerequisites:** {', '.join(phase.prerequisites)}\n")
                sections.append("**Success criteria:**\n")
                for sc in phase.success_criteria:
                    sections.append(f"- {sc}")
                if phase.milestones:
                    sections.append("\n**Milestones:**\n")
                    for m in phase.milestones:
                        sections.append(f"- **{m.name}** ({m.estimated_hours:.0f}h): {m.description}")
                        for d in m.deliverables:
                            sections.append(f"  - {d}")
                sections.append("")

            if self.total_estimated_hours or self.total_estimated_weeks:
                parts = []
                if self.total_estimated_hours:
                    parts.append(f"{self.total_estimated_hours:.0f} hours")
                if self.total_estimated_weeks:
                    parts.append(f"~{self.total_estimated_weeks} weeks")
                sections.append(f"**Total across all phases:** {' / '.join(parts)}\n")

        # Legacy milestones section (for proposals without delivery_phases)
        if self.milestones and not self.delivery_phases:
            sections.append("\n## Project Milestones")
            for m in self.milestones:
                sections.append(f"### {m.name}\n{m.description}\n")
                sections.append("**Deliverables:**\n")
                for d in m.deliverables:
                    sections.append(f"- {d}")

        sections.extend([
            f"\n## Timeline\n\nEstimated duration: **{self.timeline_weeks} weeks**",
            f"\n## Investment\n\n{self.investment}",
        ])

        # Key risks
        if self.engagement_summary.key_risks:
            sections.append("\n## Key Risks\n")
            sections.append("| Risk | Probability | Impact | Mitigation |")
            sections.append("|------|-------------|--------|------------|")
            for r in self.engagement_summary.key_risks:
                sections.append(f"| {r.risk} | {r.probability} | {r.impact} | {r.mitigation} |")

        # Assumptions and out-of-scope
        if self.engagement_summary.assumptions:
            sections.append("\n## Assumptions\n")
            for a in self.engagement_summary.assumptions:
                sections.append(f"- {a}")
        if self.engagement_summary.out_of_scope:
            sections.append("\n## Out of Scope\n")
            for o in self.engagement_summary.out_of_scope:
                sections.append(f"- {o}")

        return "\n".join(sections)
