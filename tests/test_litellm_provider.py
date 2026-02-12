"""Tests for LiteLLM provider and model mapping (Phase 2)."""

import pytest
from unittest.mock import patch, MagicMock

from providers.litellm_provider import _to_litellm_model, LiteLLMProvider
from providers.base import LLMResponse


class TestToLiteLLMModel:
    """Test _to_litellm_model mapping."""

    def test_openai_default(self):
        assert _to_litellm_model("openai", None) == "gpt-4o-mini"

    def test_openai_explicit_model(self):
        assert _to_litellm_model("openai", "gpt-4o") == "gpt-4o"
        assert _to_litellm_model("openai", "gpt-4o-mini") == "gpt-4o-mini"

    def test_anthropic_default(self):
        assert "anthropic" in _to_litellm_model("anthropic", None)
        assert "claude" in _to_litellm_model("anthropic", None).lower()

    def test_anthropic_haiku(self):
        assert "haiku" in _to_litellm_model("anthropic", "claude-haiku").lower()

    def test_gemini_default(self):
        assert _to_litellm_model("gemini", None) == "gemini/gemini-2.0-flash"

    def test_gemini_explicit(self):
        assert _to_litellm_model("gemini", "gemini-2.5-pro") == "gemini/gemini-2.5-pro"

    def test_deepseek_default(self):
        assert "deepseek" in _to_litellm_model("deepseek", None).lower()

    def test_no_provider_model_only(self):
        # model only: should resolve from aliases or pass through
        out = _to_litellm_model(None, "gpt-4o-mini")
        assert out == "gpt-4o-mini" or "gpt" in out.lower()

    def test_no_provider_no_model(self):
        assert _to_litellm_model(None, None) == "gpt-4o-mini"

    def test_tier_names_pass_through(self):
        # Tier names are not remapped by _to_litellm_model; provider uses them as-is for Router
        assert _to_litellm_model(None, "tier1") in ("tier1", "gpt-4o-mini")  # may alias
        # With a provider, "tier1" might not be in MODEL_ALIASES for openai, so could return tier1
        out = _to_litellm_model("openai", "tier1")
        assert out == "tier1" or "gpt" in out.lower()


class TestLiteLLMProvider:
    """Test LiteLLMProvider with mocked litellm."""

    @pytest.fixture
    def mock_completion_response(self):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = "Hello, world."
        resp.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        resp._hidden_params = {"response_cost": 0.001}
        resp.model = "gpt-4o-mini"
        return resp

    def test_complete_returns_llm_response(self, mock_completion_response):
        with patch("litellm.completion", return_value=mock_completion_response):
            with patch("providers.cost_logger.get_swarm_cost_logger"):
                provider = LiteLLMProvider(default_model="gpt-4o-mini")
                result = provider.complete("You are helpful.", "Hi", max_tokens=100)
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello, world."
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.cost == 0.001
        assert result.model == "gpt-4o-mini"
        assert result.provider == "litellm"

    def test_complete_passes_metadata(self, mock_completion_response):
        with patch("litellm.completion", return_value=mock_completion_response) as mock_completion:
            with patch("providers.cost_logger.get_swarm_cost_logger"):
                provider = LiteLLMProvider(default_model="gpt-4o-mini", metadata={"agent": "discovery", "tier": "tier1"})
                provider.complete("Sys", "User")
        call_kw = mock_completion.call_args[1]
        assert call_kw.get("metadata") == {"agent": "discovery", "tier": "tier1"}

    def test_tier_model_uses_router(self, mock_completion_response):
        mock_router = MagicMock()
        mock_router.completion.return_value = mock_completion_response
        with patch("litellm.completion") as mock_lt_completion:
            with patch("providers.router.create_router", return_value=mock_router):
                with patch("providers.cost_logger.get_swarm_cost_logger"):
                    # Force fresh router (get_router uses singleton)
                    import providers.router as router_mod
                    router_mod._tier_router = None
                    provider = LiteLLMProvider(default_model="tier1")
                    result = provider.complete("Sys", "User", model="tier1")
        mock_router.completion.assert_called_once()
        call_kw = mock_router.completion.call_args[1]
        assert call_kw["model"] == "tier1"
        mock_lt_completion.assert_not_called()
        assert result.content == "Hello, world."

    def test_set_metadata(self):
        provider = LiteLLMProvider(default_model="gpt-4o-mini")
        provider.set_metadata({"agent": "critic"})
        provider.set_metadata({"tier": "tier2"})
        assert provider._metadata == {"agent": "critic", "tier": "tier2"}

    def test_name_and_default_model(self):
        provider = LiteLLMProvider(default_model="gemini/gemini-2.0-flash")
        assert provider.name == "litellm"
        assert provider.default_model == "gemini/gemini-2.0-flash"

    def test_is_available(self):
        assert LiteLLMProvider(default_model="gpt-4o-mini").is_available() is True
        assert LiteLLMProvider(default_model="").is_available() is False
