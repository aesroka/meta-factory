"""Base swarm class for orchestrating agents with critic loops.

Provides the common infrastructure for running agents with critique,
handling feedback loops, and tracking costs.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel

from agents import BaseAgent, CriticAgent, TokenUsage
from librarian import Librarian
from contracts import CriticVerdict, Objection, HumanEscalation
from config import settings


T = TypeVar("T", bound=BaseModel)


@dataclass
class SwarmRun:
    """Record of a swarm execution."""
    run_id: str
    mode: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    critic_logs: Dict[str, List[CriticVerdict]] = field(default_factory=dict)
    escalations: List[HumanEscalation] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    status: str = "running"
    error: Optional[str] = None


class BaseSwarm(ABC):
    """Base class for swarm orchestration.

    Provides:
    - Agent execution with critic review loops
    - Cost tracking and circuit breakers
    - Artifact storage and retrieval
    - Error handling and escalation
    """

    def __init__(
        self,
        librarian: Optional[Librarian] = None,
        run_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the swarm.

        Args:
            librarian: Shared librarian instance
            run_id: Unique identifier for this run
            provider: LLM provider for agents (anthropic, openai, gemini, deepseek)
            model: Model name for agents
        """
        self.librarian = librarian or Librarian()
        self.run_id = run_id or self._generate_run_id()
        self.run = SwarmRun(run_id=self.run_id, mode=self.mode_name)
        self._cost_exceeded = False
        self.provider = provider
        self.model = model

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return the mode name (greenfield, brownfield, greyfield)."""
        pass

    def _generate_run_id(self) -> str:
        """Generate a unique run ID."""
        from datetime import datetime
        return f"{self.mode_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _check_cost_limit(self) -> bool:
        """Check if cost limit has been exceeded.

        Returns:
            True if under limit, False if exceeded
        """
        current_cost = self.run.token_usage.total_cost
        if current_cost >= settings.max_cost_per_run_usd:
            self._cost_exceeded = True
            return False
        return True

    def _update_token_usage(self, agent: BaseAgent) -> None:
        """Update total token usage from an agent's run."""
        self.run.token_usage.input_tokens += agent.total_usage.input_tokens
        self.run.token_usage.output_tokens += agent.total_usage.output_tokens

    def run_with_critique(
        self,
        agent: BaseAgent,
        input_data: BaseModel,
        stage_name: str,
        rerun_fn: Optional[Callable[[BaseModel, List[Objection]], BaseModel]] = None,
    ) -> tuple[BaseModel, bool, Optional[HumanEscalation]]:
        """Run an agent with critic review loop.

        Args:
            agent: The agent to run
            input_data: Input data for the agent
            stage_name: Name of this stage for logging
            rerun_fn: Optional function to regenerate output with feedback.
                     If not provided, uses agent.run with enriched input.

        Returns:
            Tuple of (artifact, passed_review, escalation_or_none)
        """
        if not self._check_cost_limit():
            escalation = HumanEscalation(
                artifact={"error": "Cost limit exceeded"},
                review_log=[],
                reason=f"Cost limit of ${settings.max_cost_per_run_usd} exceeded",
                suggested_resolution="Increase cost limit or reduce scope",
            )
            return input_data, False, escalation

        # Run the agent
        result = agent.run(input_data)
        self._update_token_usage(agent)
        current_output = result.output

        # Create critic for this agent
        critic = CriticAgent(
            agent.role,
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        all_objections: List[Objection] = []
        verdicts: List[CriticVerdict] = []

        # Critic loop
        for iteration in range(settings.max_critic_iterations):
            if not self._check_cost_limit():
                break

            verdict = critic.review(current_output, iteration, all_objections)
            verdicts.append(verdict)
            self.run.token_usage.input_tokens += critic.total_usage.input_tokens
            self.run.token_usage.output_tokens += critic.total_usage.output_tokens

            if verdict.passed:
                self.run.critic_logs[stage_name] = verdicts
                self.run.artifacts[stage_name] = current_output
                return current_output, True, None

            # Collect objections
            all_objections.extend(verdict.objections)

            # Check if we should re-run
            if iteration < settings.max_critic_iterations - 1:
                if rerun_fn:
                    current_output = rerun_fn(current_output, verdict.objections)
                else:
                    # Default: re-run agent with enriched input
                    enriched_input = self._enrich_with_feedback(input_data, verdict)
                    result = agent.run(enriched_input)
                    self._update_token_usage(agent)
                    current_output = result.output

        # Max iterations reached - escalate if objections remain
        self.run.critic_logs[stage_name] = verdicts

        if all_objections:
            escalation = HumanEscalation(
                artifact=current_output.model_dump() if hasattr(current_output, 'model_dump') else current_output,
                review_log=all_objections,
                reason="Max critic iterations reached with unresolved objections",
                suggested_resolution=f"Manual review required for {stage_name}",
                context=f"Stage: {stage_name}, Iterations: {len(verdicts)}",
            )
            self.run.escalations.append(escalation)
            self.run.artifacts[stage_name] = current_output
            return current_output, False, escalation

        self.run.artifacts[stage_name] = current_output
        return current_output, True, None

    def _enrich_with_feedback(
        self,
        input_data: BaseModel,
        verdict: CriticVerdict,
    ) -> BaseModel:
        """Enrich input data with critic feedback for retry.

        Creates a new input with feedback context added.
        """
        # Convert to dict and add feedback
        data = input_data.model_dump()

        feedback = {
            "critic_feedback": {
                "score": verdict.score,
                "objections": [
                    {
                        "category": obj.category,
                        "description": obj.description,
                        "severity": obj.severity.value,
                        "suggested_fix": obj.suggested_fix,
                    }
                    for obj in verdict.objections
                ],
                "instruction": "Address the objections listed above in your revised output.",
            }
        }

        # Add to context or create new field
        if "context" in data and isinstance(data["context"], dict):
            data["context"].update(feedback)
        else:
            data["previous_feedback"] = feedback

        return type(input_data).model_validate(data)

    def save_artifacts(self, output_dir: Optional[str] = None) -> str:
        """Save all artifacts to the output directory.

        Args:
            output_dir: Override the default output directory

        Returns:
            Path to the output directory
        """
        import json
        from pathlib import Path

        output_path = Path(output_dir or settings.output_dir) / self.run_id
        output_path.mkdir(parents=True, exist_ok=True)

        # Save each artifact
        for name, artifact in self.run.artifacts.items():
            artifact_path = output_path / f"{name}.json"
            if hasattr(artifact, 'model_dump'):
                data = artifact.model_dump()
            else:
                data = artifact
            artifact_path.write_text(json.dumps(data, indent=2, default=str))

        # Save run metadata
        run_meta = {
            "run_id": self.run.run_id,
            "mode": self.run.mode,
            "started_at": self.run.started_at.isoformat(),
            "completed_at": self.run.completed_at.isoformat() if self.run.completed_at else None,
            "status": self.run.status,
            "token_usage": {
                "input_tokens": self.run.token_usage.input_tokens,
                "output_tokens": self.run.token_usage.output_tokens,
                "total_cost_usd": self.run.token_usage.total_cost,
            },
            "escalations": len(self.run.escalations),
        }
        (output_path / "run_metadata.json").write_text(json.dumps(run_meta, indent=2))

        # Save escalations if any
        if self.run.escalations:
            escalations_data = [
                {
                    "artifact_type": type(e.artifact).__name__ if hasattr(e.artifact, '__class__') else str(type(e.artifact)),
                    "reason": e.reason,
                    "suggested_resolution": e.suggested_resolution,
                    "objection_count": len(e.review_log),
                }
                for e in self.run.escalations
            ]
            (output_path / "escalations.json").write_text(json.dumps(escalations_data, indent=2))

        return str(output_path)

    @abstractmethod
    def execute(self, input_data: Any) -> Dict[str, Any]:
        """Execute the swarm pipeline.

        Args:
            input_data: Input appropriate for this swarm type

        Returns:
            Dictionary of final artifacts
        """
        pass
