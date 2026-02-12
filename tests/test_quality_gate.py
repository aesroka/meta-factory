"""Tests for Phase 5 Quality Gate: critic tier routing, escalation, budget warning."""

import io
import pytest
from unittest.mock import Mock, patch, MagicMock

from agents.critic_agent import CriticAgent
from agents.base_agent import BaseAgent, AgentResult, TokenUsage
from agents.discovery_agent import DiscoveryAgent, DiscoveryInput
from contracts import CriticVerdict, Objection, Severity
from pydantic import BaseModel


# --- Test 1: Critic routes through tier2 ---


class TestCriticTier2Routing:
    """CriticAgent with no explicit model uses model == 'tier2' and routes through tier2."""

    def test_critic_agent_model_is_tier2_when_no_model_provided(self):
        """Instantiate CriticAgent(reviewing_agent_role='discovery') with no model; assert agent.model == 'tier2'."""
        with patch("agents.critic_agent.get_provider"):
            critic = CriticAgent("discovery")
        assert critic.model == "tier2"

    def test_critic_completion_called_with_model_tier2(self):
        """Mock litellm.completion and verify the model passed to the provider is 'tier2'."""
        with patch("agents.critic_agent.get_provider") as p_get_provider:
            mock_provider = MagicMock()
            mock_provider.complete = MagicMock(
                return_value=MagicMock(
                    content='{"passed": false, "score": 0.5, "objections": [], "iteration": 0, "max_iterations": 3, "summary": "Ok"}',
                    input_tokens=10,
                    output_tokens=20,
                )
            )
            p_get_provider.return_value = mock_provider
            critic = CriticAgent("discovery")
            # Minimal artifact for review
            class DummyArtifact(BaseModel):
                x: str = "test"
            critic.review(DummyArtifact(), 0, [])
        mock_provider.complete.assert_called_once()
        call_kw = mock_provider.complete.call_args[1]
        assert call_kw.get("model") == "tier2"


# --- Test 2: Tier escalation on second retry ---


def _verdict_fail(iteration: int) -> CriticVerdict:
    return CriticVerdict(
        passed=False,
        score=0.5,
        objections=[
            Objection(
                category="completeness",
                description="Missing item",
                bible_reference="Test",
                severity=Severity.MAJOR,
            )
        ],
        iteration=iteration,
        summary="Fail",
    )


def _verdict_pass(iteration: int) -> CriticVerdict:
    return CriticVerdict(
        passed=True,
        score=0.9,
        objections=[],
        iteration=iteration,
        summary="Pass",
    )


class TestTierEscalation:
    """On second critic failure, agent re-run is called with model='tier3'."""

    def test_escalation_on_second_retry(self):
        """Mock critic to fail twice then pass. Verify first re-run: model=None; second re-run: model='tier3'."""
        from swarms.base_swarm import BaseSwarm

        # Concrete swarm that only implements abstract run()
        class ConcreteSwarm(BaseSwarm):
            def run(self, input_data):
                return input_data

        swarm = ConcreteSwarm()
        input_data = DiscoveryInput(transcript="test", context="")
        # Agent whose run() we will mock to record calls and return a valid output
        agent = DiscoveryAgent()
        out1, out2, out3 = MagicMock(), MagicMock(), MagicMock()
        for o in (out1, out2, out3):
            o.model_dump.return_value = {"x": "y"}
        agent.run = Mock(
            side_effect=[
                AgentResult(output=out1, token_usage=TokenUsage(), model="tier1", provider="openai"),
                AgentResult(output=out2, token_usage=TokenUsage(), model="tier1", provider="openai"),
                AgentResult(output=out3, token_usage=TokenUsage(), model="tier3", provider="openai"),
            ]
        )

        with patch("swarms.base_swarm.CriticAgent") as MockCritic:
            mock_critic_instance = MagicMock()
            mock_critic_instance.review.side_effect = [
                _verdict_fail(0),
                _verdict_fail(1),
                _verdict_pass(2),
            ]
            mock_critic_instance.total_usage = TokenUsage()
            MockCritic.return_value = mock_critic_instance

            artifact, passed, escalation = swarm.run_with_critique(
                agent, input_data, "discovery"
            )

        assert agent.run.call_count == 3
        # First call: initial run — no model override
        assert agent.run.call_args_list[0][1].get("model") is None
        # Second call: first retry (iteration 0) — no escalation
        assert agent.run.call_args_list[1][1].get("model") is None
        # Third call: second retry (iteration 1) — escalation to tier3
        assert agent.run.call_args_list[2][1].get("model") == "tier3"
        assert passed is True
        assert escalation is None


# --- Test 3: Budget warning ---


class TestBudgetWarning:
    """Budget warning fires when total_cost >= 80% of max_budget."""

    def test_budget_warning_fires_at_80_percent(self):
        """Set litellm.max_budget=1.0, log one event with cost 0.85, assert warning in stdout."""
        impl = __import__("providers.cost_logger", fromlist=["_get_swarm_logger_impl"])
        get_impl = getattr(impl, "_get_swarm_logger_impl", None)
        if get_impl is None:
            pytest.skip("cost_logger layout changed")
        SwarmCostLogger = get_impl()
        if SwarmCostLogger is None:
            pytest.skip("litellm not available")
        logger = SwarmCostLogger()
        logger.total_cost = 0.0
        logger.calls = []

        response_obj = MagicMock()
        response_obj._hidden_params = {"response_cost": 0.85}
        kwargs = {"model": "gpt-4o", "litellm_params": {}, "metadata": {}}

        try:
            import litellm
        except ImportError:
            pytest.skip("litellm not installed")
        with patch.object(litellm, "max_budget", 1.0):
            with patch("sys.stdout", new_callable=io.StringIO) as buf:
                logger.log_success_event(kwargs, response_obj, None, None)
                out = buf.getvalue()
        assert "BUDGET WARNING" in out
        assert "0.85" in out or "0.8" in out


# --- Test 4: No escalation when critic passes first time ---


class TestNoEscalationWhenPassFirstTime:
    """When critic passes on first review, agent.run() is called exactly once with no model override."""

    def test_agent_run_called_once_no_model_override(self):
        """Mock critic to pass immediately. Verify agent.run called exactly once with no model override."""
        from swarms.base_swarm import BaseSwarm

        class ConcreteSwarm(BaseSwarm):
            def run(self, input_data):
                return input_data

        swarm = ConcreteSwarm()
        input_data = DiscoveryInput(transcript="test", context="")
        agent = DiscoveryAgent()
        out = MagicMock()
        out.model_dump.return_value = {}
        agent.run = Mock(
            return_value=AgentResult(
                output=out,
                token_usage=TokenUsage(),
                model="tier1",
                provider="openai",
            )
        )

        with patch("swarms.base_swarm.CriticAgent") as MockCritic:
            mock_critic_instance = MagicMock()
            mock_critic_instance.review.return_value = _verdict_pass(0)
            mock_critic_instance.total_usage = TokenUsage()
            MockCritic.return_value = mock_critic_instance

            artifact, passed, escalation = swarm.run_with_critique(
                agent, input_data, "discovery"
            )

        assert agent.run.call_count == 1
        agent.run.assert_called_once_with(input_data)
        # No model keyword passed (or explicitly None)
        call_kw = agent.run.call_args[1]
        assert call_kw.get("model") is None or "model" not in call_kw
        assert passed is True
        assert escalation is None
