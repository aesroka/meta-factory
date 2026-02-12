"""Tests for the Miner Agent (Phase 3)."""

import json
import pytest
from unittest.mock import patch, MagicMock

from agents.miner_agent import MinerAgent, MINER_RAG_QUERIES
from contracts import ProjectDossier, MinerInput, Stakeholder, TechConstraint, CoreLogicFlow


def _valid_dossier_json() -> str:
    """Return a valid ProjectDossier as JSON string."""
    data = {
        "project_name": "Acme",
        "summary": "Paragraph one. Paragraph two.",
        "stakeholders": [{"name": "Alice", "role": "PM", "concerns": ["scope"]}],
        "tech_stack_detected": ["Python", "React"],
        "constraints": [
            {"category": "Security", "requirement": "SSO", "priority": "Must-have"},
        ],
        "logic_flows": [
            {"trigger": "User login", "process": "Auth", "outcome": "Session"},
        ],
        "legacy_debt_summary": None,
    }
    return json.dumps(data)


class TestMinerAgentExtract:
    """Test MinerAgent.extract() with mocked LLM."""

    def test_valid_extraction_returns_project_dossier(self):
        """Mock completion returns valid ProjectDossier JSON; extract() returns validated Dossier."""
        with patch("litellm.completion", return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=_valid_dossier_json()))],
            usage=MagicMock(prompt_tokens=10, completion_tokens=20),
            _hidden_params={"response_cost": 0.001},
            model="gpt-4o-mini",
        )):
            with patch("providers.cost_logger.get_swarm_cost_logger"):
                agent = MinerAgent(model="gpt-4o-mini")  # concrete model so we don't use Router
                result = agent.extract("Some RAG context.", "Acme", mode=None)
        assert isinstance(result, ProjectDossier)
        assert result.project_name == "Acme"
        assert len(result.stakeholders) == 1
        assert result.stakeholders[0].name == "Alice"
        assert "Python" in result.tech_stack_detected
        assert result.legacy_debt_summary is None

    def test_retry_on_malformed_json(self):
        """First call returns prose + partial JSON; second returns valid JSON. Verify retry."""
        bad_response = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Here is the result:\n{ \"project_name\": "))],
            usage=MagicMock(prompt_tokens=10, completion_tokens=5),
            _hidden_params={},
            model="gpt-4o-mini",
        )
        good_response = MagicMock(
            choices=[MagicMock(message=MagicMock(content=_valid_dossier_json()))],
            usage=MagicMock(prompt_tokens=10, completion_tokens=20),
            _hidden_params={},
            model="gpt-4o-mini",
        )
        with patch("litellm.completion", side_effect=[bad_response, good_response]):
            with patch("providers.cost_logger.get_swarm_cost_logger"):
                agent = MinerAgent(model="gpt-4o-mini")
                result = agent.extract("Context", "Acme")
        assert isinstance(result, ProjectDossier)
        assert result.project_name == "Acme"

    def test_retry_on_validation_error(self):
        """First call returns JSON that fails validation (e.g. wrong type); second returns valid Dossier."""
        invalid = {
            "project_name": "Acme",
            "summary": 123,  # wrong type: must be str
            "stakeholders": [],
            "tech_stack_detected": [],
            "constraints": [],
            "logic_flows": [],
            "legacy_debt_summary": None,
        }
        valid_str = _valid_dossier_json()
        with patch("litellm.completion", side_effect=[
            MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps(invalid)))], usage=MagicMock(prompt_tokens=10, completion_tokens=10), _hidden_params={}, model="gpt-4o-mini"),
            MagicMock(choices=[MagicMock(message=MagicMock(content=valid_str))], usage=MagicMock(prompt_tokens=10, completion_tokens=20), _hidden_params={}, model="gpt-4o-mini"),
        ]):
            with patch("providers.cost_logger.get_swarm_cost_logger"):
                agent = MinerAgent(model="gpt-4o-mini")
                result = agent.extract("Context", "Acme")
        assert isinstance(result, ProjectDossier)
        assert result.project_name == "Acme"
        assert isinstance(result.summary, str)

    def test_empty_rag_context_produces_valid_dossier(self):
        """Pass rag_context=''; Miner should still produce valid (mostly empty) Dossier."""
        empty_ok = {
            "project_name": "Empty Client",
            "summary": "No context provided. No context provided.",
            "stakeholders": [],
            "tech_stack_detected": [],
            "constraints": [],
            "logic_flows": [],
            "legacy_debt_summary": None,
        }
        with patch("litellm.completion", return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content=json.dumps(empty_ok)))],
            usage=MagicMock(prompt_tokens=5, completion_tokens=15),
            _hidden_params={},
            model="gpt-4o-mini",
        )):
            with patch("providers.cost_logger.get_swarm_cost_logger"):
                agent = MinerAgent(model="gpt-4o-mini")
                result = agent.extract("", "Empty Client")
        assert isinstance(result, ProjectDossier)
        assert result.project_name == "Empty Client"
        assert result.stakeholders == []
        assert result.tech_stack_detected == []

    def test_miner_uses_default_tier(self):
        """MinerAgent with no explicit model uses DEFAULT_TIER = tier1."""
        agent = MinerAgent()
        assert getattr(agent.__class__, "DEFAULT_TIER", None) == "tier1"
        assert agent.model == "tier1"


class TestMinerRagQueries:
    """Test MINER_RAG_QUERIES."""

    def test_miner_rag_queries_non_empty(self):
        assert len(MINER_RAG_QUERIES) >= 5
        assert any("stakeholder" in q.lower() for q in MINER_RAG_QUERIES)
        assert any("technolog" in q.lower() or "constraint" in q.lower() for q in MINER_RAG_QUERIES)
