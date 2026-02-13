# Phase 7 Completion Note: Ensemble Estimation

**Completed:** 2025-02-12

## What was done

- **7.1** `agents/estimation_ensemble.py`: OptimistEstimator, PessimistEstimator, RealistEstimator (subclasses of EstimatorAgent with BIAS_PROMPT prepended to SYSTEM_PROMPT).
- **7.2** `agents/estimation_aggregator.py`: `aggregate_ensemble(optimist, pessimist, realist)` — match tasks by normalized name; for matched tasks E=(O+4*R+P)/6, SD=(P-O)/6; derive O,M,P from E,SD; include unmatched tasks with caveat; recompute total_expected_hours, total_std_dev, confidence_interval_90.
- **7.3** GreenfieldSwarm._run_estimation(architecture, ensemble=True): when ensemble=True run three estimators (optimist, pessimist, realist) with run_with_critique, store artifacts estimate_optimist/estimate_pessimist/estimate_realist, return aggregate_ensemble(...). When ensemble=False, single EstimatorAgent as before. GreenfieldInput.ensemble added; showcase passes ensemble from args.
- **7.4** `--no-ensemble` on showcase_forge_stream.py; premium quality forces ensemble=True.
- **7.5** tests/test_estimation_ensemble.py: aggregator E/SD formula and validate_totals.

## Gotchas

- Ensemble runs three full critic loops (estimation_optimist, estimation_pessimist, estimation_realist) so cost is ~3x for estimation stage.
- Task matching is by normalized task name (strip, lower); if LLMs use different labels for the same task they won't match and will appear as unmatched in caveats.
- Brownfield/Greyfield _run_estimation not yet wired to ensemble (Phase 8 can add).

## Debt / follow-ups

- Parallelize three estimator calls (ThreadPoolExecutor) per plan.
- Wire ensemble to BrownfieldSwarm and GreyfieldSwarm _run_estimation.

## Reviewer checklist

- [ ] Run `pytest tests/test_estimation_ensemble.py -v`.
- [ ] Run `python scripts/showcase_forge_stream.py -p openai --no-ensemble` (single estimator) and without --no-ensemble (three + aggregate).
