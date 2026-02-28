"""Integration test: Greyfield swarm e2e with mocked LLM (completion_plan Task 7)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from swarms import GreyfieldSwarm, GreyfieldInput


def _critic_passed():
    return json.dumps({"passed": True, "score": 0.85, "objections": [], "iteration": 0, "max_iterations": 3, "summary": "OK", "strengths": ["Complete"]})


def _discovery_output():
    return json.dumps({
        "pain_points": [{"description": "Pain", "frequency": "daily", "cost_per_incident": None, "annual_cost": None, "source_quote": "q", "confidence": 0.9}],
        "stakeholder_needs": [],
        "total_annual_cost_of_pain": None,
        "key_constraints": [],
        "recommended_next_steps": [],
    })


def _legacy_output():
    return json.dumps({
        "seams": [{"seam_type": "object", "location": "Svc", "risk_level": "medium", "test_strategy": "Unit", "description": "Seam"}],
        "tech_debt": [{"module": "core", "debt_type": "coupling", "cyclomatic_complexity": 10, "coupling_description": "Tight", "remediation_strategy": "sprout", "estimated_effort_hours": 20}],
        "c4_diagrams": [],
        "constraints": {"hard_constraints": [], "soft_constraints": [], "no_go_zones": []},
        "summary": "Legacy.",
    })


def _architecture_output():
    return json.dumps({
        "utility_tree": {"scenarios": [{"attribute": "perf", "scenario": "Load", "importance": "H", "difficulty": "M", "stimulus": None, "response": None, "response_measure": None}]},
        "decisions": [{"decision": "Hybrid", "context": "Both", "pattern_used": "Gateway", "eip_reference": None, "trade_off": "T", "alternatives_considered": [], "failure_modes": []}],
        "trade_off_analysis": None,
        "integration_patterns": [],
        "component_diagram": None,
    })


def _estimation_output():
    return json.dumps({
        "pert_estimates": [{"task": "Build", "optimistic_hours": 80, "likely_hours": 100, "pessimistic_hours": 140, "expected_hours": 103.33, "std_dev": 10.0, "assumptions": []}],
        "cone_of_uncertainty": {"phase": "requirements_complete", "low_multiplier": 0.8, "high_multiplier": 1.2, "base_estimate": 100, "range_low": 80, "range_high": 120},
        "reference_classes": [],
        "total_expected_hours": 103.33,
        "total_std_dev": 10.0,
        "confidence_interval_90": [87.0, 120.0],
        "risk_factors": [],
        "caveats": [],
    })


def _synthesis_output():
    return json.dumps({
        "scqa": {"situation": "S", "complication": "C", "question": "Q", "answer": "A"},
        "pain_matrix": json.loads(_discovery_output()),
        "architecture_decisions": [{"decision": "Hybrid", "context": "Both", "pattern_used": "Gateway", "eip_reference": None, "trade_off": "T", "alternatives_considered": [], "failure_modes": []}],
        "estimates": [{"task": "Build", "optimistic_hours": 80, "likely_hours": 100, "pessimistic_hours": 140, "expected_hours": 103.33, "std_dev": 10.0, "assumptions": []}],
        "total_estimate": {"phase": "requirements_complete", "low_multiplier": 0.8, "high_multiplier": 1.2, "base_estimate": 100, "range_low": 80, "range_high": 120},
        "key_risks": [],
        "assumptions": [],
        "out_of_scope": [],
    })


def _proposal_output():
    return json.dumps({
        "title": "Greyfield Proposal",
        "client_name": "TestClient",
        "prepared_by": "Meta-Factory AI",
        "executive_summary": {"bottom_line": "BL", "key_benefits": ["B1"], "investment_summary": "100h", "recommended_action": "Proceed"},
        "engagement_summary": json.loads(_synthesis_output()),
        "problem_statement": "Problem",
        "proposed_solution": "Solution",
        "technical_approach": "Approach",
        "milestones": [{"name": "M1", "description": "D", "deliverables": ["D1"], "estimated_hours": 100, "dependencies": []}],
        "timeline_weeks": 3,
        "delivery_phases": [{"phase_name": "POC", "phase_type": "poc", "goal": "Prove", "success_criteria": ["Done"], "milestones": [{"name": "M1", "description": "D", "deliverables": ["D1"], "estimated_hours": 100, "dependencies": []}], "estimated_hours": 100, "estimated_weeks": 3, "estimated_cost_gbp": 15000, "can_stop_here": True, "prerequisites": []}],
        "recommended_first_phase": "POC",
        "total_estimated_hours": 100,
        "total_estimated_weeks": 3,
        "investment": "£15,000",
        "terms_and_conditions": None,
        "appendices": [],
    })


def _choose_response(kwargs):
    """Return the right JSON based on metadata (agent name) or message content."""
    meta = kwargs.get("metadata") or (kwargs.get("litellm_params") or {}).get("metadata") or {}
    agent = (meta.get("agent") or "").lower()
    # Resolve critic(c role) -> critic
    if "critic" in agent:
        return _critic_passed()
    if "legacy" in agent:
        return _legacy_output()
    if "discovery" in agent:
        return _discovery_output()
    if "architect" in agent:
        return _architecture_output()
    if "estimator" in agent:
        return _estimation_output()
    if "synthesis" in agent:
        return _synthesis_output()
    if "proposal" in agent:
        return _proposal_output()
    # Fallback: message content (order matters; be specific to avoid cross-match)
    messages = kwargs.get("messages") or []
    combined = " ".join(
        (m.get("content") or "") if isinstance(m, dict) else getattr(m, "content", "")
        for m in messages
    ).lower()
    if "criticverdict" in combined or "critical reviewer" in combined:
        return _critic_passed()
    if "archaeologist" in combined or "legacy code" in combined:
        return _legacy_output()
    if "utility tree" in combined or "atam" in combined:
        return _architecture_output()
    if "pain point" in combined or "pain_monetization" in combined:
        return _discovery_output()
    if "cone_of_uncertainty" in combined or "pert_estimates" in combined:
        return _estimation_output()
    # Synthesis before proposal: synthesis prompt mentions "Proposal agent" and "delivery_phases"
    if "synthesizer" in combined or ("merge" in combined and "artifact" in combined):
        return _synthesis_output()
    if "proposal engine" in combined or "proposal document" in combined or "minto pyramid" in combined:
        return _proposal_output()
    return _critic_passed()


# Sequential order after parallel discovery+legacy: arch, critic, est, critic, syn, critic, prop, critic
_SEQUENTIAL_RESPONSES = [
    _architecture_output(),
    _critic_passed(),
    _estimation_output(),
    _critic_passed(),
    _synthesis_output(),
    _critic_passed(),
    _proposal_output(),
    _critic_passed(),
]


@pytest.mark.integration
def test_greyfield_e2e_mocked():
    """Run GreyfieldSwarm.execute with mocked litellm; assert success and key artifacts.

    Discovery and legacy run in parallel (content-based); then sequential stages use call order.
    """
    call_count = [0]

    def fake_completion(**kwargs):
        n = call_count[0]
        call_count[0] += 1
        # First 4 calls: parallel discovery + legacy (each with critic). Use content-based.
        if n < 4:
            content = _choose_response(kwargs)
        else:
            # Sequential: arch, critic, est, critic, syn, critic, prop, critic
            idx = (n - 4) % len(_SEQUENTIAL_RESPONSES)
            content = _SEQUENTIAL_RESPONSES[idx]
        return MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50),
            _hidden_params={"response_cost": 0.01},
            model="gpt-4o-mini",
        )

    with patch("litellm.completion", side_effect=fake_completion):
        with patch("providers.cost_logger.get_swarm_cost_logger") as mock_logger:
            mock_logger.return_value = MagicMock(total_cost=0.0, calls=[], reset=lambda: None)
            from orchestrator.cost_controller import reset_cost_controller
            reset_cost_controller()
            swarm = GreyfieldSwarm(run_id="int_test_grey", provider="openai", model="gpt-4o-mini")
            input_data = GreyfieldInput(
                transcript="We need new features. Drivers use paper.",
                codebase_description="Existing monolith with core module.",
                client_name="TestClient",
            )
            result = swarm.execute(input_data)

    assert result.get("status") == "completed"
    artifacts = result.get("artifacts", {})
    assert "discovery" in artifacts
    assert "legacy_analysis" in artifacts
    assert "reconciled_constraints" in artifacts
    assert "architecture" in artifacts
    assert "estimation" in artifacts
    assert "synthesis" in artifacts
    assert "proposal" in artifacts
