"""LiteLLM Router with tier aliases (Phase 2.4).

Model list is built dynamically: only models whose provider has an API key
in the environment are included. Add/remove keys in .env and the Router adapts.
"""

import os
from typing import Any, Dict, List

_tier_router = None

# All candidate models per tier, in preference order.
# The Router will only see entries whose API key is set.
_ALL_TIER_MODELS: List[Dict[str, Any]] = [
    # Tier 0: Oracle — full-context analysis (massive context windows)
    {"model_name": "tier0", "litellm_params": {"model": "gemini/gemini-2.5-pro"}, "order": 1},
    {"model_name": "tier0", "litellm_params": {"model": "gpt-4o"}, "order": 2},
    {"model_name": "tier0", "litellm_params": {"model": "anthropic/claude-sonnet-4-20250514"}, "order": 3},
    {"model_name": "tier0", "litellm_params": {"model": "deepseek/deepseek-chat"}, "order": 4},
    # Tier 1: cheap — extraction, mining
    {"model_name": "tier1", "litellm_params": {"model": "gpt-4o-mini"}, "order": 1},
    {"model_name": "tier1", "litellm_params": {"model": "gemini/gemini-2.0-flash"}, "order": 2},
    {"model_name": "tier1", "litellm_params": {"model": "deepseek/deepseek-chat"}, "order": 3},
    {"model_name": "tier1", "litellm_params": {"model": "anthropic/claude-3-5-haiku-20241022"}, "order": 4},
    # Tier 2: mid — critic
    {"model_name": "tier2", "litellm_params": {"model": "gpt-4o-mini"}, "order": 1},
    {"model_name": "tier2", "litellm_params": {"model": "gemini/gemini-2.0-flash"}, "order": 2},
    {"model_name": "tier2", "litellm_params": {"model": "deepseek/deepseek-chat"}, "order": 3},
    {"model_name": "tier2", "litellm_params": {"model": "anthropic/claude-3-5-haiku-20241022"}, "order": 4},
    # Tier 3: expert — synthesis, proposals
    {"model_name": "tier3", "litellm_params": {"model": "gpt-4o"}, "order": 1},
    {"model_name": "tier3", "litellm_params": {"model": "gemini/gemini-2.5-pro"}, "order": 2},
    {"model_name": "tier3", "litellm_params": {"model": "deepseek/deepseek-chat"}, "order": 3},
    {"model_name": "tier3", "litellm_params": {"model": "anthropic/claude-sonnet-4-20250514"}, "order": 4},
]

# Map model prefix → env var that must be set
_PROVIDER_KEY_MAP = {
    "gpt-": "OPENAI_API_KEY",
    "gemini/": "GOOGLE_API_KEY",
    "deepseek/": "DEEPSEEK_API_KEY",
    "anthropic/": "ANTHROPIC_API_KEY",
}


def _has_key(model_string: str) -> bool:
    """Check if the provider for this model has an API key set."""
    for prefix, env_var in _PROVIDER_KEY_MAP.items():
        if model_string.startswith(prefix):
            return bool(os.environ.get(env_var, "").strip())
    # OpenAI models without prefix (e.g. "gpt-4o-mini")
    if model_string.startswith("gpt"):
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())
    return False


def get_tier_model_list() -> List[Dict[str, Any]]:
    """Build model_list filtered to providers with API keys present."""
    return [
        entry for entry in _ALL_TIER_MODELS
        if _has_key(entry["litellm_params"]["model"])
    ]


def create_router():
    """Create LiteLLM Router with tier model list and fallbacks."""
    from litellm import Router
    model_list = get_tier_model_list()
    if not model_list:
        raise RuntimeError(
            "No LLM providers configured. Set at least one API key in .env "
            "(OPENAI_API_KEY, GOOGLE_API_KEY, DEEPSEEK_API_KEY, ANTHROPIC_API_KEY)."
        )
    return Router(
        model_list=model_list,
        num_retries=2,
        fallbacks=[{"tier1": ["tier3"]}],
        enable_pre_call_checks=False,
    )


def get_router():
    """Return singleton Router instance."""
    global _tier_router
    if _tier_router is None:
        _tier_router = create_router()
    return _tier_router
