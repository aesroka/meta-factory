"""Tests for proposal diff engine (Phase 12)."""

import json
from pathlib import Path

import pytest

from contracts import ProposalDocument
from utils.proposal_diff import (
    PhaseDiff,
    ProposalDiff,
    generate_proposal_diff,
)


def _minimal_proposal(run_id: str, total_hours: float = 100, total_weeks: int = 8) -> dict:
    """Minimal valid ProposalDocument as dict for JSON."""
    from contracts.proposal_contracts import (
        ExecutiveSummary,
        SCQAFrame,
        EngagementSummary,
        DeliveryPhase,
        Milestone,
    )
    from contracts.discovery_contracts import PainMonetizationMatrix, PainPoint, Frequency
    from contracts.estimation_contracts import ConeOfUncertainty

    pain = PainPoint(
        description="Test",
        frequency=Frequency.DAILY,
        cost_per_incident=None,
        annual_cost=None,
        source_quote="Q",
        confidence=0.9,
    )
    phase = DeliveryPhase(
        phase_name="POC",
        phase_type="poc",
        goal="Test goal",
        success_criteria=["Done"],
        milestones=[
            Milestone(name="M1", description="D", deliverables=["D1"], estimated_hours=50),
        ],
        estimated_hours=total_hours,
        estimated_weeks=total_weeks,
        estimated_cost_gbp=total_hours * 100,
        can_stop_here=True,
    )
    cone = ConeOfUncertainty(
        phase="requirements_complete",
        low_multiplier=0.8,
        high_multiplier=1.2,
        base_estimate=total_hours,
        range_low=total_hours * 0.8,
        range_high=total_hours * 1.2,
    )
    doc = ProposalDocument(
        title="Test",
        client_name="Test",
        executive_summary=ExecutiveSummary(
            bottom_line="BL",
            key_benefits=["B"],
            investment_summary="I",
            recommended_action="R",
        ),
        engagement_summary=EngagementSummary(
            scqa=SCQAFrame(situation="S", complication="C", question="Q", answer="A"),
            pain_matrix=PainMonetizationMatrix(pain_points=[pain]),
            architecture_decisions=[],
            estimates=[],
            total_estimate=cone,
        ),
        problem_statement="P",
        proposed_solution="S",
        technical_approach="T",
        milestones=[],
        timeline_weeks=total_weeks,
        delivery_phases=[phase],
        total_estimated_hours=total_hours,
        total_estimated_weeks=total_weeks,
        investment="Inv",
    )
    return doc.model_dump(mode="json")


def test_phase_diff_model():
    """PhaseDiff and ProposalDiff are valid Pydantic models."""
    pd = PhaseDiff(
        phase_name="POC",
        baseline_hours=80,
        new_hours=100,
        hours_delta=20,
        baseline_cost_gbp=8000,
        new_cost_gbp=10000,
        cost_delta_gbp=2000,
    )
    assert pd.phase_name == "POC"
    assert pd.hours_delta == 20

    diff = ProposalDiff(
        baseline_run_id="run_a",
        new_run_id="run_b",
        total_hours_delta=20,
        total_cost_delta_gbp=2000,
        phases_changed=[pd],
    )
    md = diff.to_markdown()
    assert "run_b vs run_a" in md
    assert "+20h" in md or "20" in md
    assert "POC" in md


def test_generate_proposal_diff(tmp_path):
    """generate_proposal_diff produces diff from two dirs with proposal.json."""
    base_a = tmp_path / "run_a"
    base_b = tmp_path / "run_b"
    base_a.mkdir()
    base_b.mkdir()

    doc_a = _minimal_proposal("run_a", total_hours=80, total_weeks=6)
    doc_b = _minimal_proposal("run_b", total_hours=120, total_weeks=10)
    (base_a / "proposal.json").write_text(json.dumps(doc_a, default=str))
    (base_b / "proposal.json").write_text(json.dumps(doc_b, default=str))

    diff = generate_proposal_diff(base_a, base_b)
    assert diff.baseline_run_id == "run_a"
    assert diff.new_run_id == "run_b"
    assert diff.total_hours_delta == 40
    assert diff.timeline_weeks_delta == 4
    md = diff.to_markdown()
    assert "Summary" in md
    assert "40" in md or "+40" in md


def test_generate_proposal_diff_missing_file(tmp_path):
    """generate_proposal_diff raises if proposal.json missing."""
    (tmp_path / "run_a").mkdir()
    (tmp_path / "run_b").mkdir()
    (tmp_path / "run_a" / "proposal.json").write_text("{}")
    with pytest.raises(FileNotFoundError, match="New proposal not found"):
        generate_proposal_diff(tmp_path / "run_a", tmp_path / "run_b")
