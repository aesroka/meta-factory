"""Integration test: Brownfield swarm e2e with mocked LLM (completion_plan Task 6)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from swarms import BrownfieldSwarm, BrownfieldInput


def _critic_passed():
    return json.dumps({"passed": True, "score": 0.85, "objections": [], "iteration": 0, "max_iterations": 3, "summary": "OK", "strengths": ["Complete"]})


def _legacy_output():
    return json.dumps({
        "seams": [{"seam_type": "object", "location": "Service", "risk_level": "medium", "test_strategy": "Unit", "description": "Seam for injection"}],
        "tech_debt": [{"module": "core", "debt_type": "coupling", "cyclomatic_complexity": 10, "coupling_description": "Tight coupling", "remediation_strategy": "sprout", "estimated_effort_hours": 20}],
        "c4_diagrams": [],
        "constraints": {"hard_constraints": [], "soft_constraints": [], "no_go_zones": []},
        "summary": "Legacy codebase with coupling in core.",
    })


def _architecture_output():
    return json.dumps({
        "utility_tree": {"scenarios": [{"attribute": "maintainability", "scenario": "Refactor", "importance": "H", "difficulty": "M", "stimulus": None, "response": None, "response_measure": None}]},
        "decisions": [{"decision": "Strangler fig", "context": "Legacy", "pattern_used": "Strangler", "eip_reference": None, "trade_off": "Incremental", "alternatives_considered": [], "failure_modes": []}],
        "trade_off_analysis": None,
        "integration_patterns": [],
        "component_diagram": None,
    })


def _estimation_output():
    return json.dumps({
        "pert_estimates": [{"task": "Refactor", "optimistic_hours": 60, "likely_hours": 80, "pessimistic_hours": 120, "expected_hours": 83.33, "std_dev": 10.0, "assumptions": []}],
        "cone_of_uncertainty": {"phase": "requirements_complete", "low_multiplier": 0.8, "high_multiplier": 1.2, "base_estimate": 80, "range_low": 64, "range_high": 96},
        "reference_classes": [],
        "total_expected_hours": 83.33,
        "total_std_dev": 10.0,
        "confidence_interval_90": [67.0, 100.0],
        "risk_factors": [],
        "caveats": [],
    })


def _synthesis_output():
    return json.dumps({
        "scqa": {"situation": "S", "complication": "C", "question": "Q", "answer": "A"},
        "pain_matrix": {"pain_points": [{"description": "Legacy debt", "frequency": "daily", "cost_per_incident": None, "annual_cost": None, "source_quote": "coupling", "confidence": 0.8}], "stakeholder_needs": [], "total_annual_cost_of_pain": None, "key_constraints": [], "recommended_next_steps": []},
        "architecture_decisions": [{"decision": "Strangler", "context": "Legacy", "pattern_used": "Strangler", "eip_reference": None, "trade_off": "Incremental", "alternatives_considered": [], "failure_modes": []}],
        "estimates": [{"task": "Refactor", "optimistic_hours": 60, "likely_hours": 80, "pessimistic_hours": 120, "expected_hours": 83.33, "std_dev": 10.0, "assumptions": []}],
        "total_estimate": {"phase": "requirements_complete", "low_multiplier": 0.8, "high_multiplier": 1.2, "base_estimate": 80, "range_low": 64, "range_high": 96},
        "key_risks": [],
        "assumptions": [],
        "out_of_scope": [],
    })


def _proposal_output():
    return json.dumps({
        "title": "Brownfield Proposal",
        "client_name": "TestClient",
        "prepared_by": "Meta-Factory AI",
        "executive_summary": {"bottom_line": "BL", "key_benefits": ["B1"], "investment_summary": "80h", "recommended_action": "Proceed"},
        "engagement_summary": json.loads(_synthesis_output()),
        "problem_statement": "Legacy coupling.",
        "proposed_solution": "Strangler refactor.",
        "technical_approach": "Incremental.",
        "milestones": [{"name": "M1", "description": "D", "deliverables": ["D1"], "estimated_hours": 80, "dependencies": []}],
        "timeline_weeks": 3,
        "delivery_phases": [{"phase_name": "POC", "phase_type": "poc", "goal": "Prove", "success_criteria": ["Done"], "milestones": [{"name": "M1", "description": "D", "deliverables": ["D1"], "estimated_hours": 80, "dependencies": []}], "estimated_hours": 80, "estimated_weeks": 3, "estimated_cost_gbp": 12000, "can_stop_here": True, "prerequisites": []}],
        "recommended_first_phase": "POC",
        "total_estimated_hours": 80,
        "total_estimated_weeks": 3,
        "investment": "£12,000",
        "terms_and_conditions": None,
        "appendices": [],
    })


@pytest.mark.integration
def test_brownfield_e2e_mocked():
    """Run BrownfieldSwarm.execute with mocked litellm; assert success and key artifacts."""
    responses = [
        _legacy_output(),
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
            swarm = BrownfieldSwarm(run_id="int_test_brown", provider="openai", model="gpt-4o-mini")
            input_data = BrownfieldInput(
                codebase_description="Monolithic app with tight coupling in core module.",
                client_name="TestClient",
            )
            result = swarm.execute(input_data)

    assert result.get("status") == "completed"
    artifacts = result.get("artifacts", {})
    assert "legacy_analysis" in artifacts
    assert "refactoring_plan" in artifacts
    assert "estimation" in artifacts
    assert "synthesis" in artifacts
    assert "proposal" in artifacts
