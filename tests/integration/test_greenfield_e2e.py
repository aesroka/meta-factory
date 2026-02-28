"""Integration test: Greenfield swarm e2e with mocked LLM (completion_plan Task 5)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from swarms import GreenfieldSwarm, GreenfieldInput


# Minimal valid JSON outputs for each agent (and critic passed).
def _critic_passed():
    return json.dumps({"passed": True, "score": 0.85, "objections": [], "iteration": 0, "max_iterations": 3, "summary": "OK", "strengths": ["Complete"]})


def _discovery_output():
    return json.dumps({
        "pain_points": [{"description": "Paper manifests", "frequency": "daily", "cost_per_incident": None, "annual_cost": None, "source_quote": "drivers get paper", "confidence": 0.9}],
        "stakeholder_needs": [],
        "total_annual_cost_of_pain": None,
        "key_constraints": [],
        "recommended_next_steps": [],
    })


def _architecture_output():
    return json.dumps({
        "utility_tree": {"scenarios": [{"attribute": "performance", "scenario": "Load", "importance": "H", "difficulty": "M", "stimulus": None, "response": None, "response_measure": None}]},
        "decisions": [{"decision": "Use API gateway", "context": "Scale", "pattern_used": "Gateway", "eip_reference": None, "trade_off": "Latency", "alternatives_considered": [], "failure_modes": []}],
        "trade_off_analysis": None,
        "integration_patterns": [],
        "component_diagram": None,
    })


def _estimation_output():
    return json.dumps({
        "pert_estimates": [{"task": "Build", "optimistic_hours": 40, "likely_hours": 60, "pessimistic_hours": 100, "expected_hours": 63.33, "std_dev": 10.0, "assumptions": []}],
        "cone_of_uncertainty": {"phase": "requirements_complete", "low_multiplier": 0.8, "high_multiplier": 1.2, "base_estimate": 60, "range_low": 48, "range_high": 72},
        "reference_classes": [],
        "total_expected_hours": 63.33,
        "total_std_dev": 10.0,
        "confidence_interval_90": [47.0, 80.0],
        "risk_factors": [],
        "caveats": [],
    })


def _synthesis_output():
    return json.dumps({
        "scqa": {"situation": "S", "complication": "C", "question": "Q", "answer": "A"},
        "pain_matrix": json.loads(_discovery_output()),
        "architecture_decisions": [{"decision": "Use API gateway", "context": "Scale", "pattern_used": "Gateway", "eip_reference": None, "trade_off": "Latency", "alternatives_considered": [], "failure_modes": []}],
        "estimates": [{"task": "Build", "optimistic_hours": 40, "likely_hours": 60, "pessimistic_hours": 100, "expected_hours": 63.33, "std_dev": 10.0, "assumptions": []}],
        "total_estimate": {"phase": "requirements_complete", "low_multiplier": 0.8, "high_multiplier": 1.2, "base_estimate": 60, "range_low": 48, "range_high": 72},
        "key_risks": [],
        "assumptions": [],
        "out_of_scope": [],
    })


def _proposal_output():
    return json.dumps({
        "title": "Test Proposal",
        "client_name": "TestClient",
        "prepared_by": "Meta-Factory AI",
        "executive_summary": {"bottom_line": "BL", "key_benefits": ["B1"], "investment_summary": "60h", "recommended_action": "Proceed"},
        "engagement_summary": json.loads(_synthesis_output()),
        "problem_statement": "Problem",
        "proposed_solution": "Solution",
        "technical_approach": "Approach",
        "milestones": [{"name": "M1", "description": "D", "deliverables": ["D1"], "estimated_hours": 60, "dependencies": []}],
        "timeline_weeks": 2,
        "delivery_phases": [{"phase_name": "POC", "phase_type": "poc", "goal": "Prove", "success_criteria": ["Done"], "milestones": [{"name": "M1", "description": "D", "deliverables": ["D1"], "estimated_hours": 60, "dependencies": []}], "estimated_hours": 60, "estimated_weeks": 2, "estimated_cost_gbp": 9000, "can_stop_here": True, "prerequisites": []}],
        "recommended_first_phase": "POC",
        "total_estimated_hours": 60,
        "total_estimated_weeks": 2,
        "investment": "£9,000",
        "terms_and_conditions": None,
        "appendices": [],
    })


@pytest.mark.integration
def test_greenfield_e2e_mocked():
    """Run GreenfieldSwarm.execute with mocked litellm; assert success and artifact keys."""
    responses = [
        _discovery_output(),
        _critic_passed(),
        _architecture_output(),
        _critic_passed(),
        _estimation_output(),
        _critic_passed(),
        _synthesis_output(),
        _critic_passed(),
        _proposal_output(),
        _critic_passed(),
    ]
    call_idx = [0]

    def fake_completion(**kwargs):
        i = call_idx[0] % len(responses)
        call_idx[0] += 1
        content = responses[i]
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
            swarm = GreenfieldSwarm(run_id="int_test_green", provider="openai", model="gpt-4o-mini")
            input_data = GreenfieldInput(
                transcript="We need a mobile app for drivers. Paper manifests are a pain.",
                client_name="TestClient",
                ensemble=False,
            )
            result = swarm.execute(input_data)

    assert result.get("status") == "completed"
    artifacts = result.get("artifacts", {})
    assert "discovery" in artifacts
    assert "architecture" in artifacts
    assert "estimation" in artifacts
    assert "synthesis" in artifacts
    assert "proposal" in artifacts
    prop = artifacts["proposal"]
    assert hasattr(prop, "title") or (isinstance(prop, dict) and "title" in prop)
    assert hasattr(prop, "delivery_phases") or (isinstance(prop, dict) and "delivery_phases" in prop)
