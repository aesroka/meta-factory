"""Programmatic PERT aggregation for ensemble estimation (Phase 7)."""

import math
from typing import List, Tuple

from contracts import EstimationResult, PERTEstimate, ConeOfUncertainty


def _task_key(task_name: str) -> str:
    """Normalize task name for matching."""
    return task_name.strip().lower() or "_"


def aggregate_ensemble(
    optimist: EstimationResult,
    pessimist: EstimationResult,
    realist: EstimationResult,
) -> EstimationResult:
    """Aggregate three independent estimates using PERT formula.

    For each task that appears in all three estimates:
    E = (Optimist + 4*Realist + Pessimist) / 6
    SD = (Pessimist - Optimist) / 6

    Unmatched tasks (only in one or two) are included with a caveat.
    """
    opt_tasks = {_task_key(e.task): e for e in optimist.pert_estimates}
    pess_tasks = {_task_key(e.task): e for e in pessimist.pert_estimates}
    real_tasks = {_task_key(e.task): e for e in realist.pert_estimates}

    all_keys = set(opt_tasks) | set(pess_tasks) | set(real_tasks)
    aggregated: List[PERTEstimate] = []
    caveats: List[str] = []

    for key in sorted(all_keys):
        o_e = opt_tasks.get(key)
        p_e = pess_tasks.get(key)
        r_e = real_tasks.get(key)

        if o_e and p_e and r_e:
            # Matched: E = (O + 4*R + P)/6, SD = (P - O)/6 (using expected hours)
            e_opt = o_e.expected_hours
            e_real = r_e.expected_hours
            e_pess = p_e.expected_hours
            E = (e_opt + 4 * e_real + e_pess) / 6
            SD = (e_pess - e_opt) / 6
            SD = max(0.0, SD)
            # Derive O, M, P from E and SD so that (O+4*M+P)/6=E and (P-O)/6=SD
            O = max(0.0, E - 3 * SD)
            P = E + 3 * SD
            M = E
            task_name = r_e.task or o_e.task or p_e.task
            aggregated.append(
                PERTEstimate(
                    task=task_name,
                    optimistic_hours=round(O, 2),
                    likely_hours=round(M, 2),
                    pessimistic_hours=round(P, 2),
                    expected_hours=round(E, 2),
                    std_dev=round(SD, 2),
                    assumptions=list(set(o_e.assumptions + r_e.assumptions + p_e.assumptions))[:5],
                )
            )
        else:
            # Unmatched: take from whichever has it, add caveat
            src = o_e or r_e or p_e
            if src:
                aggregated.append(src)
                caveats.append(f"Task '{src.task}' appeared in only {'/'.join(x for x in ['optimist' if o_e else '', 'realist' if r_e else '', 'pessimist' if p_e else ''] if x)} estimate(s).")

    if not aggregated:
        # Fallback: use realist
        return realist

    total_expected = sum(e.expected_hours for e in aggregated)
    total_std = math.sqrt(sum(e.std_dev ** 2 for e in aggregated))
    ci_low = total_expected - 1.645 * total_std
    ci_high = total_expected + 1.645 * total_std
    ci_low = max(0.0, ci_low)

    cone = realist.cone_of_uncertainty
    caveats.append("Aggregated from Optimist, Realist, and Pessimist ensemble (PERT formula).")

    return EstimationResult(
        pert_estimates=aggregated,
        cone_of_uncertainty=cone,
        reference_classes=realist.reference_classes,
        total_expected_hours=round(total_expected, 2),
        total_std_dev=round(total_std, 2),
        confidence_interval_90=(round(ci_low, 2), round(ci_high, 2)),
        risk_factors=list(set(optimist.risk_factors + realist.risk_factors + pessimist.risk_factors))[:10],
        caveats=caveats,
    )
