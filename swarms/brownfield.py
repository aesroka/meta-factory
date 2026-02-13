"""Brownfield Swarm - For legacy codebase rescue/modernization.

Pipeline:
Legacy Agent → Critic → Refactoring Plan → Critic →
Estimator Agent → Critic → Synthesis Agent → Proposal Agent → Critic → OUTPUT
"""

from typing import Optional, Any, Dict
from datetime import datetime

from swarms.base_swarm import BaseSwarm
from agents import (
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
    LegacyAnalysisResult,
    ArchitectureResult,
    EstimationResult,
    EngagementSummary,
    ProposalDocument,
    PainMonetizationMatrix,
    PainPoint,
    Frequency,
    ProjectDossier,
)
from contracts.adapters import dossier_to_legacy_input
from librarian import Librarian


class BrownfieldInput:
    """Input for Brownfield swarm."""

    def __init__(
        self,
        codebase_description: str = "",
        client_name: str = "",
        code_samples: Optional[str] = None,
        known_issues: Optional[list[str]] = None,
        change_requirements: Optional[str] = None,
        dossier: Optional[ProjectDossier] = None,
        hourly_rate: float = 150.0,
    ):
        self.codebase_description = codebase_description
        self.client_name = client_name
        self.code_samples = code_samples
        self.known_issues = known_issues
        self.change_requirements = change_requirements
        self.dossier = dossier
        self.hourly_rate = hourly_rate


class BrownfieldSwarm(BaseSwarm):
    """Swarm for brownfield projects (legacy modernization).

    Pipeline:
    1. Legacy Agent (Feathers + C4) → Legacy Analysis Result
    2. Architect Agent (refactoring-focused) → Refactoring Plan
    3. Estimator Agent (with legacy risk multipliers) → Estimation Result
    4. Synthesis Agent → Engagement Summary
    5. Proposal Agent → Proposal Document

    Each stage passes through critic review before proceeding.
    """

    @property
    def mode_name(self) -> str:
        return "brownfield"

    def execute(self, input_data: BrownfieldInput) -> Dict[str, Any]:
        """Execute the brownfield pipeline.

        Args:
            input_data: BrownfieldInput with codebase info

        Returns:
            Dictionary containing all artifacts including final proposal
        """
        try:
            # Stage 1: Legacy Analysis
            legacy_result = self._run_legacy_analysis(input_data)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 2: Refactoring Plan (using Architect with legacy context)
            pain_matrix = self._create_pain_matrix_from_legacy(legacy_result, input_data)
            architecture = self._run_refactoring_plan(legacy_result, pain_matrix)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 3: Estimation (with legacy risk factors)
            estimation = self._run_estimation(architecture, legacy_result)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 4: Synthesis
            summary = self._run_synthesis(pain_matrix, architecture, estimation, legacy_result)
            if self._cost_exceeded:
                return self._finalize_run("cost_exceeded")

            # Stage 5: Proposal
            proposal = self._run_proposal(
                summary,
                input_data.client_name,
                hourly_rate=getattr(input_data, "hourly_rate", 150.0),
            )

            return self._finalize_run("completed")

        except Exception as e:
            self.run.error = str(e)
            return self._finalize_run("error")

    def _run_legacy_analysis(self, input_data: BrownfieldInput) -> LegacyAnalysisResult:
        """Run the legacy analysis stage."""
        agent = LegacyAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        if input_data.dossier is not None:
            codebase_description = dossier_to_legacy_input(input_data.dossier)
        else:
            codebase_description = input_data.codebase_description or ""
        agent_input = LegacyInput(
            codebase_description=codebase_description,
            code_samples=input_data.code_samples,
            known_issues=input_data.known_issues,
            change_requirements=input_data.change_requirements,
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="legacy_analysis",
        )

        return output

    def _create_pain_matrix_from_legacy(
        self,
        legacy: LegacyAnalysisResult,
        input_data: BrownfieldInput,
    ) -> PainMonetizationMatrix:
        """Create a pain matrix from legacy analysis findings.

        Converts technical debt and issues into business pain points.
        """
        pain_points = []

        # Convert tech debt items to pain points
        for debt in legacy.tech_debt:
            pain_points.append(PainPoint(
                description=f"Technical debt in {debt.module}: {debt.debt_type}",
                frequency=Frequency.DAILY,  # Tech debt is ongoing
                cost_per_incident=debt.estimated_effort_hours * 100,  # Rough cost estimate
                annual_cost=debt.estimated_effort_hours * 100 * 12,
                source_quote=debt.coupling_description,
                confidence=0.7,
            ))

        # Add known issues as pain points
        if input_data.known_issues:
            for issue in input_data.known_issues:
                pain_points.append(PainPoint(
                    description=issue,
                    frequency=Frequency.WEEKLY,
                    source_quote=issue,
                    confidence=0.8,
                ))

        # Ensure at least one pain point
        if not pain_points:
            pain_points.append(PainPoint(
                description="Legacy system requires modernization",
                frequency=Frequency.DAILY,
                source_quote=legacy.summary,
                confidence=0.6,
            ))

        return PainMonetizationMatrix(
            pain_points=pain_points,
            stakeholder_needs=[],
            key_constraints=legacy.constraints.hard_constraints,
            recommended_next_steps=["Begin phased modernization"],
        )

    def _run_refactoring_plan(
        self,
        legacy: LegacyAnalysisResult,
        pain_matrix: PainMonetizationMatrix,
    ) -> ArchitectureResult:
        """Run the refactoring planning stage."""
        agent = ArchitectAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        agent_input = ArchitectInput(
            pain_matrix=pain_matrix,
            constraints=legacy.constraints,
            quality_priorities=["modifiability", "testability", "maintainability"],
        )

        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="refactoring_plan",
        )

        return output

    def _run_estimation(
        self,
        architecture: ArchitectureResult,
        legacy: LegacyAnalysisResult,
    ) -> EstimationResult:
        """Run the estimation stage with legacy risk factors."""
        agent = EstimatorAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )

        # Add legacy-specific risk factors
        risk_factors = [
            "Legacy system constraints",
            "Technical debt remediation",
            "Testing coverage gaps",
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
