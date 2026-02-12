"""Tests for Dossier-primed Greenfield pipeline (Phase 4)."""

import pytest
from unittest.mock import patch, MagicMock

from contracts import ProjectDossier, Stakeholder, TechConstraint, CoreLogicFlow
from contracts.adapters import dossier_to_discovery_input
from swarms import GreenfieldSwarm, GreenfieldInput


def _sample_dossier() -> ProjectDossier:
    return ProjectDossier(
        project_name="TestClient",
        summary="A brief summary. Second paragraph.",
        stakeholders=[Stakeholder(name="Alice", role="PM", concerns=["scope"])],
        tech_stack_detected=["Python"],
        constraints=[TechConstraint(category="Security", requirement="SSO", priority="Must-have")],
        logic_flows=[CoreLogicFlow(trigger="Login", process="Auth", outcome="Session")],
        legacy_debt_summary=None,
    )


class TestDossierPipeline:
    """GreenfieldInput(dossier=...) uses adapter and passes structured transcript to Discovery."""

    def test_run_discovery_with_dossier_calls_adapter(self):
        """When input has dossier, _run_discovery calls dossier_to_discovery_input with that dossier."""
        sample = _sample_dossier()
        adapter_called = []

        with patch("contracts.adapters.dossier_to_discovery_input") as mock_adapter:
            def capture(d):
                adapter_called.append(d)
                return dossier_to_discovery_input(d)
            mock_adapter.side_effect = capture
            with patch("swarms.base_swarm.BaseSwarm.run_with_critique") as mock_critique:
                from contracts import PainMonetizationMatrix, PainPoint
                from contracts.discovery_contracts import Frequency
                one_pain = PainPoint(description="X", frequency=Frequency.DAILY, cost_per_incident=None, annual_cost=None, source_quote="Q", confidence=0.9)
                mock_critique.return_value = (PainMonetizationMatrix(pain_points=[one_pain], stakeholder_needs=[], total_annual_cost_of_pain=None, key_constraints=[], recommended_next_steps=[]), True, None)
                swarm = GreenfieldSwarm(run_id="test_dossier", provider="openai", model="gpt-4o-mini")
                swarm._run_discovery(GreenfieldInput(client_name="TestClient", dossier=sample))
        assert len(adapter_called) >= 1
        assert adapter_called[0] is sample

    def test_greenfield_input_with_dossier_passes_dossier_to_adapter(self):
        """GreenfieldInput(dossier=X) causes adapter to be invoked with X when _run_discovery runs."""
        sample = _sample_dossier()
        with patch("contracts.adapters.dossier_to_discovery_input") as mock_adapter:
            from agents import DiscoveryInput
            mock_adapter.return_value = DiscoveryInput(transcript="Mock transcript.")
            with patch("swarms.base_swarm.BaseSwarm.run_with_critique") as mock_critique:
                from contracts import PainMonetizationMatrix
                from contracts import PainPoint
                from contracts.discovery_contracts import Frequency
                one_pain = PainPoint(description="X", frequency=Frequency.DAILY, cost_per_incident=None, annual_cost=None, source_quote="Q", confidence=0.9)
                mock_critique.return_value = (PainMonetizationMatrix(pain_points=[one_pain], stakeholder_needs=[], total_annual_cost_of_pain=None, key_constraints=[], recommended_next_steps=[]), True, None)
                swarm = GreenfieldSwarm(run_id="test_full", provider="openai", model="gpt-4o-mini")
                pain = swarm._run_discovery(GreenfieldInput(client_name="TestClient", dossier=sample))
            mock_adapter.assert_called_once_with(sample)
            assert pain is not None
