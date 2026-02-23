"""Generate diffs between two proposal runs."""

from pathlib import Path
from typing import List

from pydantic import BaseModel

from contracts import ProposalDocument


class PhaseDiff(BaseModel):
    """Diff for a single phase that exists in both proposals."""
    phase_name: str
    baseline_hours: float
    new_hours: float
    hours_delta: float
    baseline_cost_gbp: float
    new_cost_gbp: float
    cost_delta_gbp: float
    milestones_added: List[str] = []
    milestones_removed: List[str] = []


class ProposalDiff(BaseModel):
    """Diff between two proposals."""
    baseline_run_id: str
    new_run_id: str
    baseline_total_hours: float = 0.0
    baseline_total_cost_gbp: float = 0.0

    total_hours_delta: float = 0.0
    total_cost_delta_gbp: float = 0.0
    timeline_weeks_delta: int = 0

    phases_added: List[str] = []
    phases_removed: List[str] = []
    phases_changed: List[PhaseDiff] = []

    risks_added: List[str] = []
    risks_removed: List[str] = []

    pain_points_delta: int = 0
    architecture_decisions_delta: int = 0

    def _percent_change(self, delta: float, baseline: float) -> float:
        if not baseline:
            return 0.0
        return delta / baseline

    def to_markdown(self) -> str:
        """Render diff as markdown report."""
        lines = [
            f"# Proposal Diff: {self.new_run_id} vs {self.baseline_run_id}",
            "",
            "## Summary",
            f"- **Total hours:** {self.total_hours_delta:+.0f}h ({self._percent_change(self.total_hours_delta, self.baseline_total_hours):.0%} change)",
            f"- **Total cost:** £{self.total_cost_delta_gbp:+,.0f}",
            f"- **Timeline:** {self.timeline_weeks_delta:+d} weeks",
            "",
        ]

        if self.phases_removed:
            lines.append("## Removed Phases")
            for p in self.phases_removed:
                lines.append(f"- ❌ {p}")
            lines.append("")

        if self.phases_added:
            lines.append("## Added Phases")
            for p in self.phases_added:
                lines.append(f"- ✅ {p}")
            lines.append("")

        if self.phases_changed:
            lines.append("## Changed Phases")
            for pc in self.phases_changed:
                lines.append(f"### {pc.phase_name}")
                lines.append(f"- Hours: {pc.baseline_hours:.0f}h → {pc.new_hours:.0f}h ({pc.hours_delta:+.0f}h)")
                lines.append(f"- Cost: £{pc.baseline_cost_gbp:,.0f} → £{pc.new_cost_gbp:,.0f} (£{pc.cost_delta_gbp:+,.0f})")
                if pc.milestones_added:
                    lines.append(f"- Added milestones: {', '.join(pc.milestones_added)}")
                if pc.milestones_removed:
                    lines.append(f"- Removed milestones: {', '.join(pc.milestones_removed)}")
                lines.append("")

        if self.risks_removed:
            lines.append("## Risks Removed")
            for r in self.risks_removed:
                lines.append(f"- {r}")
            lines.append("")
        if self.risks_added:
            lines.append("## Risks Added")
            for r in self.risks_added:
                lines.append(f"- {r}")
            lines.append("")

        lines.append("## Other")
        lines.append(f"- Pain points: {self.pain_points_delta:+d}")
        lines.append(f"- Architecture decisions: {self.architecture_decisions_delta:+d}")
        return "\n".join(lines)


def generate_proposal_diff(baseline_path: Path, new_path: Path) -> ProposalDiff:
    """Compare two proposal artifacts and generate diff.

    Args:
        baseline_path: Path to baseline run directory (containing proposal.json).
        new_path: Path to new run directory (containing proposal.json).

    Returns:
        ProposalDiff instance.
    """
    baseline_file = baseline_path / "proposal.json"
    new_file = new_path / "proposal.json"
    if not baseline_file.exists():
        raise FileNotFoundError(f"Baseline proposal not found: {baseline_file}")
    if not new_file.exists():
        raise FileNotFoundError(f"New proposal not found: {new_file}")

    baseline = ProposalDocument.model_validate_json(baseline_file.read_text())
    new_doc = ProposalDocument.model_validate_json(new_file.read_text())

    baseline_phases = {p.phase_name: p for p in baseline.delivery_phases}
    new_phases = {p.phase_name: p for p in new_doc.delivery_phases}

    phases_added = [n for n in new_phases if n not in baseline_phases]
    phases_removed = [n for n in baseline_phases if n not in new_phases]

    phases_changed: List[PhaseDiff] = []
    for name in set(baseline_phases) & set(new_phases):
        bp = baseline_phases[name]
        np = new_phases[name]
        if bp.estimated_hours != np.estimated_hours or (bp.estimated_cost_gbp or 0) != (np.estimated_cost_gbp or 0):
            baseline_milestone_names = {m.name for m in bp.milestones}
            new_milestone_names = {m.name for m in np.milestones}
            phases_changed.append(
                PhaseDiff(
                    phase_name=name,
                    baseline_hours=bp.estimated_hours,
                    new_hours=np.estimated_hours,
                    hours_delta=np.estimated_hours - bp.estimated_hours,
                    baseline_cost_gbp=bp.estimated_cost_gbp or 0,
                    new_cost_gbp=np.estimated_cost_gbp or 0,
                    cost_delta_gbp=(np.estimated_cost_gbp or 0) - (bp.estimated_cost_gbp or 0),
                    milestones_added=list(new_milestone_names - baseline_milestone_names),
                    milestones_removed=list(baseline_milestone_names - new_milestone_names),
                )
            )

    baseline_total_hours = baseline.total_estimated_hours or sum(
        p.estimated_hours for p in baseline.delivery_phases
    )
    new_total_hours = new_doc.total_estimated_hours or sum(
        p.estimated_hours for p in new_doc.delivery_phases
    )
    baseline_total_cost = sum(p.estimated_cost_gbp or 0 for p in baseline.delivery_phases)
    new_total_cost = sum(p.estimated_cost_gbp or 0 for p in new_doc.delivery_phases)

    baseline_risks = {r.risk for r in baseline.engagement_summary.key_risks}
    new_risks = {r.risk for r in new_doc.engagement_summary.key_risks}
    risks_added = list(new_risks - baseline_risks)
    risks_removed = list(baseline_risks - new_risks)

    return ProposalDiff(
        baseline_run_id=baseline_path.name,
        new_run_id=new_path.name,
        baseline_total_hours=baseline_total_hours,
        baseline_total_cost_gbp=baseline_total_cost,
        total_hours_delta=new_total_hours - baseline_total_hours,
        total_cost_delta_gbp=new_total_cost - baseline_total_cost,
        timeline_weeks_delta=(new_doc.total_estimated_weeks or new_doc.timeline_weeks or 0)
        - (baseline.total_estimated_weeks or baseline.timeline_weeks or 0),
        phases_added=phases_added,
        phases_removed=phases_removed,
        phases_changed=phases_changed,
        risks_added=risks_added,
        risks_removed=risks_removed,
        pain_points_delta=(
            len(new_doc.engagement_summary.pain_matrix.pain_points)
            - len(baseline.engagement_summary.pain_matrix.pain_points)
        ),
        architecture_decisions_delta=(
            len(new_doc.engagement_summary.architecture_decisions)
            - len(baseline.engagement_summary.architecture_decisions)
        ),
    )
