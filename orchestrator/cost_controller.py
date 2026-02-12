"""Cost controller for tracking and limiting API usage costs.

Reads from SwarmCostLogger (LiteLLM callback); provides budget checks and per-run manifests.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

from config import settings


def _logger():
    from providers.cost_logger import get_swarm_cost_logger
    return get_swarm_cost_logger()


@dataclass
class TokenUsage:
    """Token usage for a single API call (legacy; real cost comes from SwarmCostLogger)."""
    input_tokens: int
    output_tokens: int
    model: str
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def cost(self) -> float:
        """Calculate cost based on settings."""
        return settings.calculate_cost(self.input_tokens, self.output_tokens)


@dataclass
class AgentCostRecord:
    """Cost record for a single agent execution (legacy; detailed data from logger.calls)."""
    agent_name: str
    stage_name: str
    usage: TokenUsage
    iteration: int = 0


class CostController:
    """Thin reporting layer over SwarmCostLogger. Tracks budget and generates manifests."""

    def __init__(self, max_cost_usd: Optional[float] = None):
        """Initialize the cost controller and reset the swarm cost logger for this run."""
        self.max_cost_usd = max_cost_usd or settings.max_cost_per_run_usd
        _logger().reset()

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens (not provided by logger; 0)."""
        return 0

    @property
    def total_output_tokens(self) -> int:
        """Total output tokens (not provided by logger; 0)."""
        return 0

    @property
    def total_cost_usd(self) -> float:
        """Total cost in USD from SwarmCostLogger."""
        return _logger().total_cost

    @property
    def remaining_budget_usd(self) -> float:
        """Remaining budget in USD."""
        return max(0, self.max_cost_usd - self.total_cost_usd)

    @property
    def is_budget_exceeded(self) -> bool:
        """Check if budget has been exceeded."""
        return self.total_cost_usd >= self.max_cost_usd

    @property
    def is_circuit_broken(self) -> bool:
        """True if budget exceeded (LiteLLM raises BudgetExceededError at hard limit)."""
        return self.is_budget_exceeded

    def record_usage(
        self,
        agent_name: str,
        stage_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        iteration: int = 0,
    ) -> bool:
        """No-op; cost is tracked by LiteLLM callback. Kept for API compatibility."""
        return not self.is_budget_exceeded

    def check_budget(self, estimated_cost: float = 0.0) -> bool:
        """Check if budget allows for an estimated additional cost."""
        return (self.total_cost_usd + estimated_cost) < self.max_cost_usd

    def get_cost_by_agent(self) -> Dict[str, float]:
        """Get cost breakdown by agent from SwarmCostLogger.calls."""
        costs: Dict[str, float] = {}
        for c in _logger().calls:
            agent = c.get("agent", "unknown")
            costs[agent] = costs.get(agent, 0) + float(c.get("cost", 0))
        return costs

    def get_cost_by_stage(self) -> Dict[str, float]:
        """By-stage not available from logger; returns by-agent as proxy."""
        return self.get_cost_by_agent()

    def generate_manifest(self) -> Dict[str, Any]:
        """Generate a cost manifest from SwarmCostLogger data."""
        total = self.total_cost_usd
        calls = _logger().calls
        return {
            "summary": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": round(total, 4),
                "max_budget_usd": self.max_cost_usd,
                "budget_used_percent": round(
                    (total / self.max_cost_usd * 100) if self.max_cost_usd > 0 else 0, 1
                ),
                "circuit_broken": self.is_budget_exceeded,
            },
            "by_agent": {k: round(v, 4) for k, v in self.get_cost_by_agent().items()},
            "by_stage": {k: round(v, 4) for k, v in self.get_cost_by_stage().items()},
            "detailed_records": [
                {
                    "agent": c.get("agent", "unknown"),
                    "tier": c.get("tier", "?"),
                    "model": c.get("model", "unknown"),
                    "cost_usd": round(float(c.get("cost", 0)), 4),
                }
                for c in calls
            ],
        }

    def save_manifest(self, output_path: Path) -> str:
        """Save cost manifest to file.

        Args:
            output_path: Directory to save manifest

        Returns:
            Path to saved manifest file
        """
        manifest = self.generate_manifest()
        manifest_path = output_path / "cost_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return str(manifest_path)


# Global cost controller for the current run
_current_controller: Optional[CostController] = None


def get_cost_controller() -> CostController:
    """Get the current cost controller, creating one if needed."""
    global _current_controller
    if _current_controller is None:
        _current_controller = CostController()
    return _current_controller


def reset_cost_controller(max_cost_usd: Optional[float] = None) -> CostController:
    """Reset the cost controller for a new run and set LiteLLM global budget."""
    global _current_controller
    budget = max_cost_usd if max_cost_usd is not None else settings.max_cost_per_run_usd
    _current_controller = CostController(budget)
    try:
        import litellm
        litellm.max_budget = budget
    except Exception:
        pass
    return _current_controller
