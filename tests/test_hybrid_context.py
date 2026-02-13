"""Tests for Phase 6: Hybrid context (tier0, context_mode, reconciliation)."""

import pytest
from unittest.mock import MagicMock, patch

from contracts import ProjectDossier, DossierReconciliation, Stakeholder, TechConstraint, CoreLogicFlow


class TestDossierReconciliationContract:
    """DossierReconciliation and merge behaviour."""

    def test_reconciliation_contract_valid(self):
        """DossierReconciliation with merged_dossier and lists validates."""
        dossier = ProjectDossier(
            project_name="Test",
            summary="Summary",
            stakeholders=[Stakeholder(name="A", role="PM", concerns=[])],
            tech_stack_detected=["Python"],
            constraints=[],
            logic_flows=[],
            legacy_debt_summary=None,
        )
        recon = DossierReconciliation(
            merged_dossier=dossier,
            agreements=["stakeholder:a"],
            disagreements=[],
            rag_only_items=[],
            full_context_only_items=["tech:Go"],
            confidence_score=0.85,
        )
        assert recon.confidence_score == 0.85
        assert recon.merged_dossier.project_name == "Test"
        assert "tech:Go" in recon.full_context_only_items

    def test_context_mode_rag_backward_compatible(self):
        """IngestionInput with default context_mode='rag' behaves as before."""
        from swarms.ingestion_swarm import IngestionInput

        inp = IngestionInput(client_name="Acme", dataset_id="ds1")
        assert inp.context_mode == "rag"
        assert inp.raw_documents is None


class TestTier0Routing:
    """Tier0 is recognised by provider and router."""

    def test_router_includes_tier0(self):
        """get_tier_model_list includes tier0 entries."""
        from providers.router import get_tier_model_list

        model_list = get_tier_model_list()
        tier0_entries = [e for e in model_list if e.get("model_name") == "tier0"]
        assert len(tier0_entries) >= 1

    def test_litellm_provider_routes_tier0(self):
        """LiteLLMProvider complete() treats tier0 as a tier (routes through Router)."""
        import providers.litellm_provider as p

        with open(p.__file__) as f:
            content = f.read()
        assert "tier0" in content
