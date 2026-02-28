"""Greenfield Swarm - For new projects starting from scratch.

Pipeline:
Discovery Agent → Critic → Architect Agent → Critic →
Estimator Agent → Critic → Synthesis Agent → Proposal Agent → Critic → OUTPUT
"""

import json
from pathlib import Path
from typing import Optional, Any, Dict, TYPE_CHECKING
from datetime import datetime

from swarms.base_swarm import BaseSwarm
from agents import (
    DiscoveryAgent,
    DiscoveryInput,
    ArchitectAgent,
    ArchitectInput,
    EstimatorAgent,
    EstimatorInput,
    SynthesisAgent,
    SynthesisInput,
    ProposalAgent,
    ProposalInput,
)
from contracts import (
    PainMonetizationMatrix,
    ArchitectureResult,
    EstimationResult,
    EngagementSummary,
    ProposalDocument,
)
from librarian import Librarian

if TYPE_CHECKING:
    from contracts import ProjectDossier


class GreenfieldInput:
    """Input for Greenfield swarm."""

    def __init__(
        self,
        transcript: str = "",
        client_name: str = "",
        context: Optional[str] = None,
        quality_priorities: Optional[list[str]] = None,
        dossier: Optional["ProjectDossier"] = None,
        ensemble: bool = True,
        hourly_rate: float = 150.0,
    ):
        self.transcript = transcript
        self.client_name = client_name
        self.context = context
        self.quality_priorities = quality_priorities
        self.dossier = dossier
        self.ensemble = ensemble
        self.hourly_rate = hourly_rate


class GreenfieldSwarm(BaseSwarm):
    """Swarm for greenfield projects (new builds from scratch).

    Pipeline:
    1. Discovery Agent (Mom Test + SPIN) → Pain Monetization Matrix
    2. Architect Agent (EIP + ATAM) → Architecture Result
    3. Estimator Agent (McConnell) → Estimation Result
    4. Synthesis Agent → Engagement Summary
    5. Proposal Agent (Minto + SCQA) → Proposal Document

    Each stage passes through critic review before proceeding.
    """

    @property
    def mode_name(self) -> str:
        return "greenfield"

    def _run_stage_with_retry(self, stage_name: str, stage_fn, *args, **kwargs):
        """Run a stage once; on failure retry once, then raise."""
        import time
        import structlog
        logger = structlog.get_logger()
        self._emit_progress(stage_name, "started")
        logger.info("stage_started", stage=stage_name, mode=self.mode_name)
        start = time.time()
        from orchestrator.cost_controller import get_cost_controller
        cost_before = get_cost_controller().total_cost_usd
        try:
            out = stage_fn(*args, **kwargs)
            duration = time.time() - start
            cost_after = get_cost_controller().total_cost_usd
            stage_cost = cost_after - cost_before
            get_cost_controller().record_stage(
                stage=stage_name,
                duration_s=round(duration, 2),
                cost_usd=stage_cost,
            )
            self._emit_progress(stage_name, "completed", duration_s=round(duration, 2), cost_usd=stage_cost)
            logger.info(
                "stage_completed",
                stage=stage_name,
                duration_s=round(duration, 2),
                cost_exceeded=getattr(self, "_cost_exceeded", False),
            )
            return out
        except Exception as e:
            duration = time.time() - start
            self.run.error = str(e)
            self._emit_progress(stage_name, "failed", duration_s=round(duration, 2), error=str(e))
            logger.error(
                "stage_failed",
                stage=stage_name,
                duration_s=round(duration, 2),
                error=str(e),
            )
            try:
                cost_before_retry = get_cost_controller().total_cost_usd
                out = stage_fn(*args, **kwargs)
                self.run.error = None
                duration2 = time.time() - start
                cost_after_retry = get_cost_controller().total_cost_usd
                get_cost_controller().record_stage(
                    stage=stage_name,
                    duration_s=round(duration2, 2),
                    cost_usd=cost_after_retry - cost_before_retry,
                )
                self._emit_progress(stage_name, "completed", duration_s=round(duration2, 2), cost_usd=cost_after_retry - cost_before_retry)
                logger.info(
                    "stage_completed",
                    stage=stage_name,
                    duration_s=round(duration2, 2),
                    cost_exceeded=getattr(self, "_cost_exceeded", False),
                )
                return out
            except Exception as e2:
                self.run.error = str(e2)
                self._emit_progress(stage_name, "failed", duration_s=round(time.time() - start, 2), error=str(e2))
                logger.error(
                    "stage_failed",
                    stage=stage_name,
                    duration_s=round(time.time() - start, 2),
                    error=str(e2),
                )
                raise

    def execute(self, input_data: GreenfieldInput) -> Dict[str, Any]:
        """Execute the greenfield pipeline.

        Args:
            input_data: GreenfieldInput with transcript and client info

        Returns:
            Dictionary containing all artifacts including final proposal
        """
        try:
            # Stage 1: Discovery
            pain_matrix = self._run_stage_with_retry("discovery", self._run_discovery, input_data)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 2: Architecture
            architecture = self._run_stage_with_retry(
                "architecture",
                self._run_architecture,
                pain_matrix,
                input_data.quality_priorities,
            )
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 3: Estimation
            estimation = self._run_stage_with_retry(
                "estimation",
                self._run_estimation,
                architecture,
                ensemble=getattr(input_data, "ensemble", True),
            )
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 4: Synthesis
            summary = self._run_stage_with_retry(
                "synthesis",
                self._run_synthesis,
                pain_matrix,
                architecture,
                estimation,
            )
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 5: Proposal
            proposal = self._run_stage_with_retry(
                "proposal",
                self._run_proposal,
                summary,
                input_data.client_name,
                hourly_rate=getattr(input_data, "hourly_rate", 150.0),
            )

            return self._finalize_run("completed")

        except Exception as e:
            self.run.error = str(e)
            return self._finalize_run("error")

    def execute_resume(
        self,
        output_dir: Path,
        client_name: str,
        hourly_rate: float = 150.0,
        ensemble: bool = True,
    ) -> Dict[str, Any]:
        """Load artifacts from a previous run and continue from the next stage.

        Only runs missing stages; writes back to output_dir.
        """
        output_dir = Path(output_dir)
        if not output_dir.is_dir():
            raise FileNotFoundError(f"Resume directory not found: {output_dir}")

        # Load run_metadata for token usage
        meta_path = output_dir / "run_metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            tu = meta.get("token_usage", {})
            self.run.token_usage.input_tokens = tu.get("input_tokens", 0)
            self.run.token_usage.output_tokens = tu.get("output_tokens", 0)

        # Load artifacts (map filename -> artifact name and type)
        loaders = [
            ("discovery.json", "discovery", PainMonetizationMatrix),
            ("architecture.json", "architecture", ArchitectureResult),
            ("estimation.json", "estimation", EstimationResult),
            ("synthesis.json", "synthesis", EngagementSummary),
            ("proposal.json", "proposal", ProposalDocument),
        ]
        for filename, name, model_cls in loaders:
            path = output_dir / filename
            if path.exists():
                data = json.loads(path.read_text())
                self.run.artifacts[name] = model_cls.model_validate(data)

        # Determine next stage
        if "proposal" in self.run.artifacts:
            return self._finalize_run("completed")
        if "synthesis" in self.run.artifacts:
            summary = self.run.artifacts["synthesis"]
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")
            proposal = self._run_stage_with_retry(
                "proposal",
                self._run_proposal,
                summary,
                client_name,
                hourly_rate=hourly_rate,
            )
            self.run.artifacts["proposal"] = proposal
            return self._finalize_run("completed")
        if "estimation" in self.run.artifacts:
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")
            pain_matrix = self.run.artifacts["discovery"]
            architecture = self.run.artifacts["architecture"]
            estimation = self.run.artifacts["estimation"]
            summary = self._run_stage_with_retry(
                "synthesis",
                self._run_synthesis,
                pain_matrix,
                architecture,
                estimation,
            )
            self.run.artifacts["synthesis"] = summary
            proposal = self._run_stage_with_retry(
                "proposal",
                self._run_proposal,
                summary,
                client_name,
                hourly_rate=hourly_rate,
            )
            self.run.artifacts["proposal"] = proposal
            return self._finalize_run("completed")
        if "architecture" in self.run.artifacts:
            pain_matrix = self.run.artifacts["discovery"]
            architecture = self.run.artifacts["architecture"]
            estimation = self._run_stage_with_retry(
                "estimation",
                self._run_estimation,
                architecture,
                ensemble=ensemble,
            )
            self.run.artifacts["estimation"] = estimation
            summary = self._run_stage_with_retry(
                "synthesis",
                self._run_synthesis,
                pain_matrix,
                architecture,
                estimation,
            )
            self.run.artifacts["synthesis"] = summary
            proposal = self._run_stage_with_retry(
                "proposal",
                self._run_proposal,
                summary,
                client_name,
                hourly_rate=hourly_rate,
            )
            self.run.artifacts["proposal"] = proposal
            return self._finalize_run("completed")
        if "discovery" in self.run.artifacts:
            # Run from architecture onward
            pain_matrix = self.run.artifacts["discovery"]
            architecture = self._run_stage_with_retry(
                "architecture",
                self._run_architecture,
                pain_matrix,
                None,
            )
            self.run.artifacts["architecture"] = architecture
            estimation = self._run_stage_with_retry(
                "estimation",
                self._run_estimation,
                architecture,
                ensemble=ensemble,
            )
            self.run.artifacts["estimation"] = estimation
            summary = self._run_stage_with_retry(
                "synthesis",
                self._run_synthesis,
                pain_matrix,
                architecture,
                estimation,
            )
            self.run.artifacts["synthesis"] = summary
            proposal = self._run_stage_with_retry(
                "proposal",
                self._run_proposal,
                summary,
                client_name,
                hourly_rate=hourly_rate,
            )
            self.run.artifacts["proposal"] = proposal
            return self._finalize_run("completed")

        raise ValueError(
            f"No greenfield artifacts found in {output_dir}. "
            "Need at least discovery.json to resume."
        )

    def _run_discovery(self, input_data: GreenfieldInput) -> PainMonetizationMatrix:
        """Run the discovery stage. If dossier is provided, use it as structured input for Discovery."""
        agent = DiscoveryAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        if input_data.dossier is not None:
            from contracts.adapters import dossier_to_discovery_input
            agent_input = dossier_to_discovery_input(input_data.dossier)
        else:
            agent_input = DiscoveryInput(
                transcript=input_data.transcript,
                context=input_data.context,
            )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="discovery",
        )

        return output

    def _run_architecture(
        self,
        pain_matrix: PainMonetizationMatrix,
        quality_priorities: Optional[list[str]] = None,
    ) -> ArchitectureResult:
        """Run the architecture stage."""
        agent = ArchitectAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        agent_input = ArchitectInput(
            pain_matrix=pain_matrix,
            quality_priorities=quality_priorities,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="architecture",
        )

        return output

    def _run_estimation(self, architecture: ArchitectureResult, ensemble: bool = True) -> EstimationResult:
        """Run the estimation stage (single agent or ensemble of Optimist/Pessimist/Realist)."""
        agent_input = EstimatorInput(
            architecture_decisions=architecture.decisions,
            project_phase="requirements_complete",
        )

        if not ensemble:
            if getattr(self, "use_reference_forecast", False):
                from agents.reference_estimator import ReferenceEstimator
                agent = ReferenceEstimator(
                    librarian=self.librarian,
                    provider=self.provider,
                    model=self.model,
                )
            else:
                agent = EstimatorAgent(
                    librarian=self.librarian,
                    provider=self.provider,
                    model=self.model,
                )
            output, _passed, _escalation = self.run_with_critique(
                agent=agent,
                input_data=agent_input,
                stage_name="estimation",
            )
            return output

        from agents.estimation_ensemble import OptimistEstimator, PessimistEstimator, RealistEstimator
        from agents.estimation_aggregator import aggregate_ensemble

        opt_agent = OptimistEstimator(librarian=self.librarian, provider=self.provider, model=self.model)
        pess_agent = PessimistEstimator(librarian=self.librarian, provider=self.provider, model=self.model)
        real_agent = RealistEstimator(librarian=self.librarian, provider=self.provider, model=self.model)

        opt_output, _, _ = self.run_with_critique(opt_agent, agent_input, stage_name="estimation_optimist")
        self.run.artifacts["estimate_optimist"] = opt_output
        if not self._check_cost_limit():
            return opt_output

        pess_output, _, _ = self.run_with_critique(pess_agent, agent_input, stage_name="estimation_pessimist")
        self.run.artifacts["estimate_pessimist"] = pess_output
        if not self._check_cost_limit():
            return aggregate_ensemble(opt_output, pess_output, pess_output)

        real_output, _, _ = self.run_with_critique(real_agent, agent_input, stage_name="estimation_realist")
        self.run.artifacts["estimate_realist"] = real_output
        return aggregate_ensemble(opt_output, pess_output, real_output)

    def _run_synthesis(
        self,
        pain_matrix: PainMonetizationMatrix,
        architecture: ArchitectureResult,
        estimation: EstimationResult,
    ) -> EngagementSummary:
        """Run the synthesis stage."""
        agent = SynthesisAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        agent_input = SynthesisInput(
            pain_matrix=pain_matrix,
            architecture_result=architecture,
            estimation_result=estimation,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="synthesis",
        )

        return output

    def _run_proposal(
        self,
        summary: EngagementSummary,
        client_name: str,
        hourly_rate: float = 150.0,
    ) -> ProposalDocument:
        """Run the proposal stage."""
        agent = ProposalAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        agent_input = ProposalInput(
            engagement_summary=summary,
            client_name=client_name,
            hourly_rate_gbp=hourly_rate,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="proposal",
        )

        return output

    def _finalize_run(self, status: str) -> Dict[str, Any]:
        """Finalize the run and return results."""
        from orchestrator.cost_controller import get_cost_controller
        self.run.status = status
        self.run.completed_at = datetime.now()

        # Save artifacts
        output_path = self.save_artifacts()

        result = {
            "run_id": self.run.run_id,
            "status": status,
            "output_path": output_path,
            "artifacts": self.run.artifacts,
            "escalations": self.run.escalations,
            "token_usage": {
                "input_tokens": self.run.token_usage.input_tokens,
                "output_tokens": self.run.token_usage.output_tokens,
                "cost_usd": get_cost_controller().total_cost_usd,
            },
        }
        if self.run.error is not None:
            result["error"] = self.run.error or "Unknown error"
        return result