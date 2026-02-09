"""Cost controller for tracking and limiting API usage costs.

Provides token budget tracking, circuit breakers, and per-run cost manifests.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path

from config import settings


@dataclass
class TokenUsage:
    """Token usage for a single API call."""
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
    """Cost record for a single agent execution."""
    agent_name: str
    stage_name: str
    usage: TokenUsage
    iteration: int = 0


class CostController:
    """Tracks and limits API usage costs for a run.

    Features:
    - Per-agent cost tracking
    - Running total with budget checks
    - Circuit breaker for cost overruns
    - Cost manifest generation
    """

    def __init__(self, max_cost_usd: Optional[float] = None):
        """Initialize the cost controller.

        Args:
            max_cost_usd: Maximum allowed cost. Defaults to settings value.
        """
        self.max_cost_usd = max_cost_usd or settings.max_cost_per_run_usd
        self.records: List[AgentCostRecord] = []
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._circuit_broken = False

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens used."""
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        """Total output tokens used."""
        return self._total_output_tokens

    @property
    def total_cost_usd(self) -> float:
        """Total cost in USD."""
        return settings.calculate_cost(self._total_input_tokens, self._total_output_tokens)

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
        """Check if circuit breaker has tripped."""
        return self._circuit_broken

    def record_usage(
        self,
        agent_name: str,
        stage_name: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
        iteration: int = 0,
    ) -> bool:
        """Record token usage from an agent call.

        Args:
            agent_name: Name of the agent
            stage_name: Name of the pipeline stage
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            model: Model used for the call
            iteration: Critic iteration number if applicable

        Returns:
            True if within budget, False if budget exceeded
        """
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )

        record = AgentCostRecord(
            agent_name=agent_name,
            stage_name=stage_name,
            usage=usage,
            iteration=iteration,
        )

        self.records.append(record)
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens

        # Check budget
        if self.is_budget_exceeded:
            self._circuit_broken = True
            return False

        return True

    def check_budget(self, estimated_cost: float = 0.0) -> bool:
        """Check if budget allows for an estimated additional cost.

        Args:
            estimated_cost: Estimated cost of the next operation

        Returns:
            True if budget allows, False otherwise
        """
        return (self.total_cost_usd + estimated_cost) < self.max_cost_usd

    def get_cost_by_agent(self) -> Dict[str, float]:
        """Get cost breakdown by agent."""
        costs: Dict[str, float] = {}
        for record in self.records:
            key = record.agent_name
            costs[key] = costs.get(key, 0) + record.usage.cost
        return costs

    def get_cost_by_stage(self) -> Dict[str, float]:
        """Get cost breakdown by pipeline stage."""
        costs: Dict[str, float] = {}
        for record in self.records:
            key = record.stage_name
            costs[key] = costs.get(key, 0) + record.usage.cost
        return costs

    def generate_manifest(self) -> Dict:
        """Generate a cost manifest for the run.

        Returns:
            Dictionary containing cost breakdown and summary
        """
        return {
            "summary": {
                "total_input_tokens": self._total_input_tokens,
                "total_output_tokens": self._total_output_tokens,
                "total_cost_usd": round(self.total_cost_usd, 4),
                "max_budget_usd": self.max_cost_usd,
                "budget_used_percent": round(
                    (self.total_cost_usd / self.max_cost_usd * 100) if self.max_cost_usd > 0 else 0, 1
                ),
                "circuit_broken": self._circuit_broken,
            },
            "by_agent": {k: round(v, 4) for k, v in self.get_cost_by_agent().items()},
            "by_stage": {k: round(v, 4) for k, v in self.get_cost_by_stage().items()},
            "detailed_records": [
                {
                    "agent": r.agent_name,
                    "stage": r.stage_name,
                    "iteration": r.iteration,
                    "input_tokens": r.usage.input_tokens,
                    "output_tokens": r.usage.output_tokens,
                    "cost_usd": round(r.usage.cost, 4),
                    "model": r.usage.model,
                    "timestamp": r.usage.timestamp.isoformat(),
                }
                for r in self.records
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
    """Reset the cost controller for a new run."""
    global _current_controller
    _current_controller = CostController(max_cost_usd)
    return _current_controller
