"""Tests for Phase 7: Ensemble estimation (aggregator + sub-agents)."""

import pytest
from contracts import (
    EstimationResult,
    PERTEstimate,
    ConeOfUncertainty,
    ArchitectureDecision,
)
from agents.estimation_aggregator import aggregate_ensemble


def _make_result(task_name: str, expected: float, std_dev: float) -> EstimationResult:
    """Build a minimal valid EstimationResult for one task."""
    O = max(0, expected - 3 * std_dev)
    P = expected + 3 * std_dev
    M = expected
    cone = ConeOfUncertainty(
        phase="requirements_complete",
        low_multiplier=0.67,
        high_multiplier=1.5,
        base_estimate=expected,
        range_low=round(0.67 * expected, 2),
        range_high=round(1.5 * expected, 2),
    )
    return EstimationResult(
        pert_estimates=[
            PERTEstimate(
                task=task_name,
                optimistic_hours=round(O, 2),
                likely_hours=round(M, 2),
                pessimistic_hours=round(P, 2),
                expected_hours=round(expected, 2),
                std_dev=round(std_dev, 2),
                assumptions=[],
            )
        ],
        cone_of_uncertainty=cone,
        reference_classes=[],
        total_expected_hours=round(expected, 2),
        total_std_dev=round(std_dev, 2),
        confidence_interval_90=(round(expected - 1.645 * std_dev, 2), round(expected + 1.645 * std_dev, 2)),
        risk_factors=[],
        caveats=[],
    )


class TestAggregateEnsemble:
    """aggregate_ensemble applies PERT across three results."""

    def test_aggregated_expected_and_sd(self):
        """E = (O + 4*R + P)/6, SD = (P-O)/6 for matched task."""
        opt = _make_result("Task A", expected=100.0, std_dev=10.0)
        real = _make_result("Task A", expected=120.0, std_dev=12.0)
        pess = _make_result("Task A", expected=150.0, std_dev=15.0)

        result = aggregate_ensemble(opt, pess, real)
        assert len(result.pert_estimates) == 1
        E = result.pert_estimates[0].expected_hours
        SD = result.pert_estimates[0].std_dev
        expected_E = (100 + 4 * 120 + 150) / 6  # 121.67
        expected_SD = (150 - 100) / 6  # 8.33
        assert abs(E - expected_E) < 0.1
        assert abs(SD - expected_SD) < 0.1

    def test_aggregated_validates_totals(self):
        """Aggregated result passes validate_totals."""
        opt = _make_result("Build API", expected=40.0, std_dev=5.0)
        real = _make_result("Build API", expected=50.0, std_dev=8.0)
        pess = _make_result("Build API", expected=70.0, std_dev=10.0)
        result = aggregate_ensemble(opt, pess, real)
        assert result.total_expected_hours >= 0
        assert result.total_std_dev >= 0
        assert len(result.confidence_interval_90) == 2
        assert result.confidence_interval_90[0] <= result.confidence_interval_90[1]
