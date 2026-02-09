"""Greyfield Swarm - For existing platform with new requirements.

Pipeline:
PARALLEL:
  ├── Discovery Agent → Critic → PainMonetizationMatrix
  └── Legacy Agent → Critic → ConstraintList + SeamAnalysis

MERGE:
  → Constraint Reconciler (merges discovery needs with legacy constraints)
  → Architect Agent (receives BOTH matrices)
  → Estimator → Synthesis → Proposal → OUTPUT
"""

from typing import Optional, Any, Dict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from swarms.base_swarm import BaseSwarm
from agents import (
    DiscoveryAgent,
    DiscoveryInput,
    LegacyAgent,
    LegacyInput,
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
    LegacyAnalysisResult,
    ArchitectureResult,
    EstimationResult,
    EngagementSummary,
    ProposalDocument,
    ConstraintList,
)
from librarian import Librarian


class GreyfieldInput:
    """Input for Greyfield swarm."""

    def __init__(
        self,
        transcript: str,
        codebase_description: str,
        client_name: str,
        context: Optional[str] = None,
        code_samples: Optional[str] = None,
        known_issues: Optional[list[str]] = None,
        quality_priorities: Optional[list[str]] = None,
    ):
        self.transcript = transcript
        self.codebase_description = codebase_description
        self.client_name = client_name
        self.context = context
        self.code_samples = code_samples
        self.known_issues = known_issues
        self.quality_priorities = quality_priorities


class GreyfieldSwarm(BaseSwarm):
    """Swarm for greyfield projects (existing platform + new requirements).

    This is the most complex swarm, running discovery and legacy analysis
    in parallel, then merging the results.

    Pipeline:
    1. PARALLEL:
       - Discovery Agent → Pain Monetization Matrix
       - Legacy Agent → Legacy Analysis Result
    2. Constraint Reconciler → Merged constraints
    3. Architect Agent (with both inputs) → Architecture Result
    4. Estimator Agent → Estimation Result
    5. Synthesis Agent → Engagement Summary
    6. Proposal Agent → Proposal Document

    Each stage passes through critic review before proceeding.
    """

    @property
    def mode_name(self) -> str:
        return "greyfield"

    def execute(self, input_data: GreyfieldInput) -> Dict[str, Any]:
        """Execute the greyfield pipeline.

        Args:
            input_data: GreyfieldInput with both transcript and codebase info

        Returns:
            Dictionary containing all artifacts including final proposal
        """
        try:
            # Stage 1: Parallel Discovery + Legacy Analysis
            pain_matrix, legacy_result = self._run_parallel_analysis(input_data)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 2: Reconcile constraints
            reconciled_constraints = self._reconcile_constraints(pain_matrix, legacy_result)
            self.run.artifacts["reconciled_constraints"] = reconciled_constraints

            # Stage 3: Architecture (with both inputs)
            architecture = self._run_architecture(
                pain_matrix,
                legacy_result,
                reconciled_constraints,
                input_data.quality_priorities,
            )
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 4: Estimation
            estimation = self._run_estimation(architecture, legacy_result)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 5: Synthesis
            summary = self._run_synthesis(pain_matrix, architecture, estimation, legacy_result)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 6: Proposal
            proposal = self._run_proposal(summary, input_data.client_name)

            return self._finalize_run("completed")

        except Exception as e:
            self.run.error = str(e)
            return self._finalize_run("error")

    def _run_parallel_analysis(
        self,
        input_data: GreyfieldInput,
    ) -> tuple[PainMonetizationMatrix, LegacyAnalysisResult]:
        """Run discovery and legacy analysis in parallel."""
        discovery_result = None
        legacy_result = None

        # Run in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks
            discovery_future = executor.submit(
                self._run_discovery,
                input_data.transcript,
                input_data.context,
            )
            legacy_future = executor.submit(
                self._run_legacy_analysis,
                input_data.codebase_description,
                input_data.code_samples,
                input_data.known_issues,
            )

            # Collect results
            for future in as_completed([discovery_future, legacy_future]):
                if future == discovery_future:
                    discovery_result = future.result()
                else:
                    legacy_result = future.result()

        return discovery_result, legacy_result

    def _run_discovery(
        self,
        transcript: str,
        context: Optional[str],
    ) -> PainMonetizationMatrix:
        """Run the discovery analysis."""
        agent = DiscoveryAgent(librarian=self.librarian)
        agent_input = DiscoveryInput(
            transcript=transcript,
            context=context,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="discovery",
        )

        return output

    def _run_legacy_analysis(
        self,
        codebase_description: str,
        code_samples: Optional[str],
        known_issues: Optional[list[str]],
    ) -> LegacyAnalysisResult:
        """Run the legacy analysis."""
        agent = LegacyAgent(librarian=self.librarian)
        agent_input = LegacyInput(
            codebase_description=codebase_description,
            code_samples=code_samples,
            known_issues=known_issues,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="legacy_analysis",
        )

        return output

    def _reconcile_constraints(
        self,
        pain_matrix: PainMonetizationMatrix,
        legacy: LegacyAnalysisResult,
    ) -> ConstraintList:
        """Reconcile constraints from discovery needs and legacy limitations.

        Identifies conflicts between what stakeholders want and what the
        legacy system can support.
        """
        # Combine constraints from both sources
        hard_constraints = list(legacy.constraints.hard_constraints)
        soft_constraints = list(legacy.constraints.soft_constraints)
        no_go_zones = list(legacy.constraints.no_go_zones)

        # Add discovery constraints
        hard_constraints.extend(pain_matrix.key_constraints)

        # Identify potential conflicts
        conflicts = []
        for need in pain_matrix.stakeholder_needs:
            # Check if need conflicts with legacy constraints
            need_lower = need.need.lower()
            for constraint in legacy.constraints.hard_constraints:
                constraint_lower = constraint.lower()
                # Simple conflict detection (could be enhanced with LLM)
                if any(word in need_lower for word in ["real-time", "api", "integration"]):
                    if "no api" in constraint_lower or "batch only" in constraint_lower:
                        conflicts.append(
                            f"Conflict: {need.role} needs '{need.need}' but legacy has constraint '{constraint}'"
                        )

        # Add conflicts as soft constraints (require resolution)
        soft_constraints.extend(conflicts)

        return ConstraintList(
            hard_constraints=hard_constraints,
            soft_constraints=soft_constraints,
            no_go_zones=no_go_zones,
        )

    def _run_architecture(
        self,
        pain_matrix: PainMonetizationMatrix,
        legacy: LegacyAnalysisResult,
        constraints: ConstraintList,
        quality_priorities: Optional[list[str]],
    ) -> ArchitectureResult:
        """Run architecture planning with both discovery and legacy context."""
        agent = ArchitectAgent(librarian=self.librarian)

        # Merge constraints
        merged_constraints = ConstraintList(
            hard_constraints=constraints.hard_constraints + legacy.constraints.hard_constraints,
            soft_constraints=constraints.soft_constraints + legacy.constraints.soft_constraints,
            no_go_zones=legacy.constraints.no_go_zones,
        )

        agent_input = ArchitectInput(
            pain_matrix=pain_matrix,
            constraints=merged_constraints,
            quality_priorities=quality_priorities or ["modifiability", "performance"],
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="architecture",
        )

        return output

    def _run_estimation(
        self,
        architecture: ArchitectureResult,
        legacy: LegacyAnalysisResult,
    ) -> EstimationResult:
        """Run estimation with greyfield risk factors."""
        agent = EstimatorAgent(librarian=self.librarian)

        risk_factors = [
            "Integration with existing platform",
            "Legacy system constraints",
            "New + existing code interaction",
        ]

        agent_input = EstimatorInput(
            architecture_decisions=architecture.decisions,
            project_phase="requirements_complete",
            risk_factors=risk_factors,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="estimation",
        )

        return output

    def _run_synthesis(
        self,
        pain_matrix: PainMonetizationMatrix,
        architecture: ArchitectureResult,
        estimation: EstimationResult,
        legacy: LegacyAnalysisResult,
    ) -> EngagementSummary:
        """Run synthesis with all context."""
        agent = SynthesisAgent(librarian=self.librarian)
        agent_input = SynthesisInput(
            pain_matrix=pain_matrix,
            architecture_result=architecture,
            estimation_result=estimation,
            legacy_analysis=legacy,
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
    ) -> ProposalDocument:
        """Run proposal generation."""
        agent = ProposalAgent(librarian=self.librarian)
        agent_input = ProposalInput(
            engagement_summary=summary,
            client_name=client_name,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="proposal",
        )

        return output

    def _finalize_run(self, status: str) -> Dict[str, Any]:
        """Finalize the run and return results."""
        self.run.status = status
        self.run.completed_at = datetime.now()

        # Save artifacts
        output_path = self.save_artifacts()

        return {
            "run_id": self.run.run_id,
            "status": status,
            "output_path": output_path,
            "artifacts": self.run.artifacts,
            "escalations": self.run.escalations,
            "token_usage": {
                "input_tokens": self.run.token_usage.input_tokens,
                "output_tokens": self.run.token_usage.output_tokens,
                "cost_usd": self.run.token_usage.total_cost,
            },
        }
