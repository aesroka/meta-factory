"""Estimator that applies reference class forecasting corrections (Phase 14)."""

import math
from typing import Optional

import structlog

from agents.estimator_agent import EstimatorAgent, EstimatorInput
from contracts import EstimationResult
from contracts.estimation_contracts import PERTEstimate
from utils.historical_db import load_historical_db

logger = structlog.get_logger()


class ReferenceEstimator(EstimatorAgent):
    """Estimator enhanced with historical reference class data."""

    def __init__(
        self,
        librarian=None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        super().__init__(
            role="estimator",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=EstimationResult,
            librarian=librarian,
            model=model,
            provider=provider,
        )
        self.historical_db = load_historical_db()

    def run(self, input_data: EstimatorInput, max_retries: int = 1, model: Optional[str] = None):
        """Run base estimator then apply reference class correction."""
        base_result = super().run(input_data, max_retries=max_retries, model=model)
        base_estimate = base_result.output

        correction = self.historical_db.get_correction_factor(mode="greenfield")
        if correction == 1.0:
            logger.info("reference_forecast_no_data", message="No historical data, using base estimate")
            return base_result

        logger.info(
            "reference_forecast_applied",
            correction_factor=correction,
            base_hours=base_estimate.total_expected_hours,
        )
        adjusted_pert = []
        for e in base_estimate.pert_estimates:
            adjusted_pert.append(
                PERTEstimate(
                    task=e.task,
                    optimistic_hours=round(e.optimistic_hours * correction, 2),
                    likely_hours=round(e.likely_hours * correction, 2),
                    pessimistic_hours=round(e.pessimistic_hours * correction, 2),
                    expected_hours=round(e.expected_hours * correction, 2),
                    std_dev=round(e.std_dev * correction, 2),
                    assumptions=e.assumptions + [f"Reference correction: {correction:.2f}x"],
                )
            )
        total_exp = sum(p.expected_hours for p in adjusted_pert)
        total_std = math.sqrt(sum(p.std_dev ** 2 for p in adjusted_pert))
        ci_low = max(0.0, total_exp - 1.645 * total_std)
        ci_high = total_exp + 1.645 * total_std
        adjusted = EstimationResult(
            pert_estimates=adjusted_pert,
            cone_of_uncertainty=base_estimate.cone_of_uncertainty,
            reference_classes=base_estimate.reference_classes,
            total_expected_hours=round(total_exp, 2),
            total_std_dev=round(total_std, 2),
            confidence_interval_90=(round(ci_low, 2), round(ci_high, 2)),
            risk_factors=base_estimate.risk_factors,
            caveats=base_estimate.caveats + [f"Reference class adjustment: {correction:.2f}x from historical data"],
        )
        return base_result.model_copy(update={"output": adjusted})
