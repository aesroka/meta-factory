"""Tests for the Ingestion Swarm (Phase 3)."""

import importlib
import json
import pytest
from unittest.mock import patch, MagicMock

from swarms import IngestionSwarm, IngestionInput
from agents.miner_agent import MINER_RAG_QUERIES
from contracts import ProjectDossier


def _valid_dossier_json() -> str:
    data = {
        "project_name": "TestClient",
        "summary": "Summary one. Summary two.",
        "stakeholders": [],
        "tech_stack_detected": ["Python"],
        "constraints": [],
        "logic_flows": [],
        "legacy_debt_summary": None,
    }
    return json.dumps(data)


class TestIngestionSwarm:
    """Test IngestionSwarm.execute() with mocked RAG and LLM."""

    def test_execute_returns_completed_with_dossier_when_rag_and_llm_mock(self):
        """Mock rag_search to return chunks; mock litellm for Miner and Critic; verify completed + artifacts."""
        canned_chunks = [{"content": "Project uses Python and React.", "similarity": 0.9}]

        def fake_rag_search(query, dataset_id=None, top_k=5, **kwargs):
            return canned_chunks

        completion_count = [0]

        def fake_completion(**kwargs):
            completion_count[0] += 1
            # Miner returns dossier; Critic returns passed verdict
            if completion_count[0] == 1:
                return MagicMock(
                    choices=[MagicMock(message=MagicMock(content=_valid_dossier_json()))],
                    usage=MagicMock(prompt_tokens=50, completion_tokens=30),
                    _hidden_params={"response_cost": 0.001},
                    model="gpt-4o-mini",
                )
            # Critic (CriticVerdict schema)
            verdict = json.dumps({
                "passed": True,
                "score": 0.9,
                "objections": [],
                "iteration": 0,
                "max_iterations": 3,
                "summary": "OK",
                "strengths": [],
            })
            return MagicMock(
                choices=[MagicMock(message=MagicMock(content=verdict))],
                usage=MagicMock(prompt_tokens=40, completion_tokens=10),
                _hidden_params={},
                model="gpt-4o-mini",
            )

        rag_search_mod = importlib.import_module("agents.tools.rag_search")
        with patch.object(rag_search_mod, "rag_search", side_effect=fake_rag_search):
            with patch("litellm.completion", side_effect=fake_completion):
                with patch("providers.cost_logger.get_swarm_cost_logger"):
                    swarm = IngestionSwarm(run_id="test_ingestion", provider="openai", model="gpt-4o-mini")
                    result = swarm.execute(IngestionInput(client_name="TestClient", dataset_id="ds1"))
        assert result.get("status") == "completed"
        artifacts = result.get("artifacts", {})
        mining = artifacts.get("mining")
        assert mining is not None
        assert isinstance(mining, ProjectDossier)
        assert mining.project_name == "TestClient"

    def test_execute_returns_gracefully_when_rag_empty(self):
        """Mock rag_search to return []; swarm should return status 'error' (no context to mine)."""
        rag_search_mod = importlib.import_module("agents.tools.rag_search")
        with patch.object(rag_search_mod, "rag_search", return_value=[]):
            swarm = IngestionSwarm(run_id="test_empty", provider="openai", model="gpt-4o-mini")
            result = swarm.execute(IngestionInput(client_name="NoRAG", dataset_id="ds1"))
        assert result.get("status") == "error"
        assert "mining" not in result.get("artifacts", {})
