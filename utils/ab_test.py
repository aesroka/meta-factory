"""A/B test utilities for comparing prompt variants (Phase 13)."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class VariantResult:
    """Result of running one variant."""
    variant: str
    cost_usd: float
    duration_s: float
    output_preview: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


def run_ab_test(
    agent_role: str,
    variants: List[str],
    input_content: str,
    client_name: str,
    max_cost_per_run: float = 5.0,
) -> "ABTestReport":
    """Run the same input through multiple prompt variants and collect results.

    Requires the agent to be invokable (e.g. discovery via GreenfieldSwarm or DiscoveryAgent).
    Returns an ABTestReport with cost, duration, and optional output preview per variant.
    """
    results: List[VariantResult] = []
    import os
    from pathlib import Path
    for variant in variants:
        os.environ["META_FACTORY_PROMPT_VARIANT"] = variant
        try:
            from swarms import GreenfieldSwarm, GreenfieldInput
            from orchestrator.cost_controller import reset_cost_controller, get_cost_controller
            import time
            reset_cost_controller(max_cost_per_run)
            swarm = GreenfieldSwarm(run_id=f"ab_{agent_role}_{variant}", provider="openai", model="gpt-4o-mini")
            start = time.time()
            pain = swarm._run_discovery(GreenfieldInput(transcript=input_content[:8000], client_name=client_name))
            duration = time.time() - start
            cost = get_cost_controller().total_cost_usd
            preview = str(pain.model_dump())[:500] if hasattr(pain, "model_dump") else str(pain)[:500]
            results.append(VariantResult(variant=variant, cost_usd=cost, duration_s=duration, output_preview=preview))
        except Exception as e:
            results.append(VariantResult(variant=variant, cost_usd=0, duration_s=0, success=False, error=str(e)))
    return ABTestReport(agent=agent_role, variants=variants, results=results)


class ABTestReport:
    """Report of an A/B test run."""

    def __init__(self, agent: str, variants: List[str], results: List[VariantResult]):
        self.agent = agent
        self.variants = variants
        self.results = results

    def to_markdown(self) -> str:
        lines = [f"# A/B Test: {self.agent}", "", "| Variant | Cost (USD) | Duration (s) | Success |", "|---------|------------|--------------|--------|"]
        for r in self.results:
            status = "✓" if r.success else f"✗ {r.error or 'failed'}"
            lines.append(f"| {r.variant} | ${r.cost_usd:.4f} | {r.duration_s:.1f} | {status} |")
        return "\n".join(lines)
