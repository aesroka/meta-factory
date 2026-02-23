"""Engagement Manager - Central orchestrator for the Meta-Factory.

The Engagement Manager is the main entry point that:
1. Accepts input and routes to the correct swarm
2. Dispatches execution to the selected swarm
3. Tracks overall progress and handles feedback loops
4. Produces final outputs and cost manifests
"""

from typing import Optional, Dict, Any, Union
from pathlib import Path
from datetime import datetime
import json

from router import Router, route_input
from contracts import Mode, RoutingDecision
from swarms import (
    GreenfieldSwarm,
    GreenfieldInput,
    BrownfieldSwarm,
    BrownfieldInput,
    GreyfieldSwarm,
    GreyfieldInput,
)
from orchestrator.cost_controller import CostController, reset_cost_controller
from librarian import Librarian
from config import settings


class EngagementManager:
    """Central state machine for orchestrating Meta-Factory runs.

    Responsibilities:
    - Route input to correct swarm
    - Dispatch and track swarm execution
    - Handle feedback loops and escalations
    - Produce final outputs with cost manifests
    """

    def __init__(
        self,
        max_cost_usd: Optional[float] = None,
        output_dir: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the Engagement Manager.

        Args:
            max_cost_usd: Maximum cost budget for the run
            output_dir: Directory for output artifacts
            provider: LLM provider (anthropic, openai, gemini, deepseek)
            model: Model name override (e.g. gpt-4o, gemini-1.5-pro)
        """
        self.max_cost_usd = max_cost_usd or settings.max_cost_per_run_usd
        self.output_dir = Path(output_dir or settings.output_dir)
        self.provider = provider
        self.model = model
        self.router = Router(provider=provider, model=model)
        self.librarian = Librarian()
        self.cost_controller = reset_cost_controller(self.max_cost_usd)

        self._current_run_id: Optional[str] = None
        self._run_started: Optional[datetime] = None

    def run(
        self,
        input_content: str,
        client_name: str,
        input_path: Optional[str] = None,
        codebase_content: Optional[str] = None,
        force_mode: Optional[Mode] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        quality: str = "standard",
        hourly_rate: float = 150.0,
        run_id: Optional[str] = None,
        baseline: Optional[str] = None,
        variation: Optional[str] = None,
        use_reference_forecast: bool = False,
    ) -> Dict[str, Any]:
        """Execute a complete Meta-Factory run.

        Args:
            input_content: Primary input (transcript, idea, or code)
            client_name: Name of the client for proposal
            input_path: Optional path for input classification hints
            codebase_content: Optional codebase content for greyfield
            force_mode: Override automatic mode selection
            provider: LLM provider override for this run
            model: Model name override for this run
            quality: standard or premium (affects ensemble estimation)
            hourly_rate: GBP per hour for cost estimates

        Returns:
            Dictionary with run results, artifacts, and cost manifest
        """
        self._run_started = datetime.now()
        self._current_run_id = run_id or f"run_{self._run_started.strftime('%Y%m%d_%H%M%S')}"
        self._baseline = baseline
        self._variation = variation
        self._use_reference_forecast = use_reference_forecast

        try:
            # Step 1: Route the input
            routing = self.router.route(input_content, input_path, force_mode)
            print(f"[Meta-Factory] Routing to {routing.mode.value} mode")

            # Step 2: Execute the appropriate swarm
            result = self._dispatch_swarm(
                routing,
                input_content,
                client_name,
                codebase_content,
                provider or self.provider,
                model or self.model,
                quality=quality,
                hourly_rate=hourly_rate,
            )

            # Step 3: Finalize and return results
            return self._finalize_run(result, routing)

        except Exception as e:
            return self._handle_error(e)

    def run_resume(
        self,
        run_id_or_path: str,
        client_name: str,
        output_dir: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        quality: str = "standard",
        hourly_rate: float = 150.0,
    ) -> Dict[str, Any]:
        """Resume from a previous run: load artifacts from outputs/RUN_ID and continue from the next stage.

        Only greenfield is supported. Requires --client (used for proposal stage).
        """
        out_base = Path(output_dir or settings.output_dir)
        path = Path(run_id_or_path)
        if path.is_absolute():
            output_path = path if path.is_dir() else path.parent
            run_id = output_path.name
        elif path.exists():
            output_path = path if path.is_dir() else path.parent
            run_id = output_path.name
        else:
            output_path = out_base / run_id_or_path
            run_id = run_id_or_path
        if not output_path.is_dir():
            raise FileNotFoundError(f"Resume directory not found: {output_path}")

        self._current_run_id = run_id
        self._run_started = datetime.now()
        self.output_dir = output_path.parent  # so _save_run_summary writes to same place
        print(f"[Meta-Factory] Resuming {run_id} (greenfield)")

        swarm = GreenfieldSwarm(
            librarian=self.librarian,
            run_id=run_id,
            provider=provider or self.provider,
            model=model or self.model,
        )
        swarm._output_dir_override = str(output_path.parent)  # save back to same dir
        result = swarm.execute_resume(
            output_dir=output_path,
            client_name=client_name,
            hourly_rate=hourly_rate,
            ensemble=(quality == "premium"),
        )
        routing = RoutingDecision(mode=Mode.GREENFIELD, config={})
        return self._finalize_run(result, routing)

    def _dispatch_swarm(
        self,
        routing: RoutingDecision,
        input_content: str,
        client_name: str,
        codebase_content: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        quality: str = "standard",
        hourly_rate: float = 150.0,
    ) -> Dict[str, Any]:
        """Dispatch execution to the appropriate swarm.

        Args:
            routing: Routing decision with mode and config
            input_content: Primary input content
            client_name: Client name
            codebase_content: Optional codebase for greyfield
            provider: LLM provider for agents
            model: Model name for agents
            quality: standard or premium (ensemble estimation)
            hourly_rate: GBP per hour for cost estimates

        Returns:
            Swarm execution results
        """
        if routing.mode == Mode.GREENFIELD:
            swarm = GreenfieldSwarm(
                librarian=self.librarian,
                run_id=self._current_run_id,
                provider=provider,
                model=model,
            )
            swarm.variation = getattr(self, "_variation", None)
            swarm.baseline = getattr(self, "_baseline", None)
            swarm.use_reference_forecast = getattr(self, "_use_reference_forecast", False)
            swarm_input = GreenfieldInput(
                transcript=input_content,
                client_name=client_name,
                ensemble=(quality == "premium"),
                hourly_rate=hourly_rate,
            )
            return swarm.execute(swarm_input)

        elif routing.mode == Mode.BROWNFIELD:
            swarm = BrownfieldSwarm(
                librarian=self.librarian,
                run_id=self._current_run_id,
                provider=provider,
                model=model,
            )
            swarm.variation = getattr(self, "_variation", None)
            swarm.baseline = getattr(self, "_baseline", None)
            swarm_input = BrownfieldInput(
                codebase_description=input_content,
                client_name=client_name,
                hourly_rate=hourly_rate,
            )
            return swarm.execute(swarm_input)

        elif routing.mode == Mode.GREYFIELD:
            if not codebase_content:
                raise ValueError("Greyfield mode requires codebase_content")

            swarm = GreyfieldSwarm(
                librarian=self.librarian,
                run_id=self._current_run_id,
                provider=provider,
                model=model,
            )
            swarm.variation = getattr(self, "_variation", None)
            swarm.baseline = getattr(self, "_baseline", None)
            swarm_input = GreyfieldInput(
                transcript=input_content,
                codebase_description=codebase_content,
                client_name=client_name,
                hourly_rate=hourly_rate,
            )
            return swarm.execute(swarm_input)

        else:
            raise ValueError(f"Unknown mode: {routing.mode}")

    def _finalize_run(
        self,
        swarm_result: Dict[str, Any],
        routing: RoutingDecision,
    ) -> Dict[str, Any]:
        """Finalize the run and produce outputs.

        Args:
            swarm_result: Results from swarm execution
            routing: Original routing decision

        Returns:
            Complete run results
        """
        run_end = datetime.now()
        duration = (run_end - self._run_started).total_seconds()

        # Add run metadata
        result = {
            "run_id": self._current_run_id,
            "mode": routing.mode.value,
            "started_at": self._run_started.isoformat(),
            "completed_at": run_end.isoformat(),
            "duration_seconds": round(duration, 2),
            **swarm_result,
        }

        # Save run summary
        self._save_run_summary(result)

        return result

    def _save_run_summary(self, result: Dict[str, Any]) -> None:
        """Save run summary to output directory."""
        output_path = self.output_dir / self._current_run_id
        output_path.mkdir(parents=True, exist_ok=True)

        summary = {
            "run_id": result["run_id"],
            "mode": result["mode"],
            "status": result.get("status", "unknown"),
            "started_at": result["started_at"],
            "completed_at": result["completed_at"],
            "duration_seconds": result["duration_seconds"],
            "token_usage": result.get("token_usage", {}),
            "escalation_count": len(result.get("escalations", [])),
            "artifacts_produced": list(result.get("artifacts", {}).keys()),
        }

        summary_path = output_path / "run_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))

    def _handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors during run execution.

        Args:
            error: The exception that occurred

        Returns:
            Error result dictionary
        """
        run_end = datetime.now()
        duration = (run_end - self._run_started).total_seconds() if self._run_started else 0

        return {
            "run_id": self._current_run_id,
            "status": "error",
            "error": str(error),
            "error_type": type(error).__name__,
            "started_at": self._run_started.isoformat() if self._run_started else None,
            "completed_at": run_end.isoformat(),
            "duration_seconds": round(duration, 2),
        }


def run_factory(
    input_content: str = "",
    client_name: str = "",
    input_path: Optional[str] = None,
    codebase_content: Optional[str] = None,
    force_mode: Optional[Mode] = None,
    max_cost_usd: Optional[float] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    quality: str = "standard",
    hourly_rate: float = 150.0,
    resume_from: Optional[str] = None,
    output_dir: Optional[str] = None,
    run_id: Optional[str] = None,
    baseline: Optional[str] = None,
    variation: Optional[str] = None,
    use_reference_forecast: bool = False,
) -> Dict[str, Any]:
    """Convenience function to run the Meta-Factory.

    Args:
        input_content: Primary input (transcript, idea, or code)
        client_name: Name of the client for proposal
        input_path: Optional path for input classification hints
        codebase_content: Optional codebase content for greyfield
        force_mode: Override automatic mode selection
        max_cost_usd: Maximum cost budget
        provider: LLM provider (anthropic, openai, gemini, deepseek)
        model: Model name (e.g. gpt-4o, gemini-1.5-pro)
        quality: standard (RAG, single estimator) or premium (hybrid, ensemble)
        hourly_rate: GBP per hour for cost estimates
        resume_from: If set, load artifacts from outputs/RUN_ID and continue from next stage
        output_dir: Output base directory (default from config)

    Returns:
        Run results dictionary
    """
    manager = EngagementManager(
        max_cost_usd=max_cost_usd,
        provider=provider,
        model=model,
    )
    if resume_from:
        return manager.run_resume(
            run_id_or_path=resume_from,
            client_name=client_name,
            output_dir=output_dir,
            provider=provider,
            model=model,
            quality=quality,
            hourly_rate=hourly_rate,
        )
    return manager.run(
        input_content=input_content,
        client_name=client_name,
        input_path=input_path,
        codebase_content=codebase_content,
        force_mode=force_mode,
        provider=provider,
        model=model,
        quality=quality,
        hourly_rate=hourly_rate,
        run_id=run_id,
        baseline=baseline,
        variation=variation,
        use_reference_forecast=use_reference_forecast,
    )
