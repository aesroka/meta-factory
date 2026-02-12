"""LiteLLM Router with tier aliases (Phase 2.4)."""

from typing import Any, Dict, List, Optional

_tier_router = None


def get_tier_model_list() -> List[Dict[str, Any]]:
    """Build model_list for tier1/tier2/tier3. Override via config if needed."""
    return [
        # Tier 1: cheap — extraction, mining
        {"model_name": "tier1", "litellm_params": {"model": "gpt-4o-mini"}},
        {"model_name": "tier1", "litellm_params": {"model": "gemini/gemini-2.0-flash"}, "order": 2},
        # Tier 2: mid — critic
        {"model_name": "tier2", "litellm_params": {"model": "gpt-4o-mini"}},
        {"model_name": "tier2", "litellm_params": {"model": "anthropic/claude-3-5-haiku-20241022"}, "order": 2},
        # Tier 3: expert — synthesis, proposals
        {"model_name": "tier3", "litellm_params": {"model": "gpt-4o"}},
        {"model_name": "tier3", "litellm_params": {"model": "anthropic/claude-sonnet-4-20250514"}, "order": 2},
    ]


def create_router():
    """Create LiteLLM Router with tier model list and fallbacks."""
    from litellm import Router
    model_list = get_tier_model_list()
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
