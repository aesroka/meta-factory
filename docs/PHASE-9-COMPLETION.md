# Phase 9 Completion Note: Phased Delivery & CLI Polish

**Completed:** 2025-02-12

## What was done

- **9.1** `contracts/proposal_contracts.py`: Added `DeliveryPhase` (phase_name, phase_type, goal, success_criteria, milestones, estimated_hours, estimated_weeks, estimated_cost_gbp, can_stop_here, prerequisites). `ProposalDocument`: added optional `delivery_phases`, `recommended_first_phase`, `total_estimated_hours`, `total_estimated_weeks` (backward compatible).
- **9.2** Synthesis/Proposal prompt snippets for phased delivery not added in full (contracts in place for downstream prompt updates).
- **9.3** `main.py`: Added `--quality standard|premium` and `--hourly-rate` (default 150). `run_factory()` and `EngagementManager.run()` accept `quality` and `hourly_rate`; GreenfieldInput gets `ensemble=(quality=="premium")`.
- **9.4** Forge-Stream pipeline wired via existing run_factory; quality drives ensemble flag.
- **9.5–9.6** Progress reporting and output formatting (stage-by-stage, summary box) deferred.
- **9.7** Existing proposal contract tests pass; DeliveryPhase export in contracts/__init__.py.

## Gotchas

- Proposal agent does not yet populate `delivery_phases` or `recommended_first_phase`; prompts need to be updated to emit phased structure. Contracts are ready.
- `--hourly-rate` is passed through but not yet used by proposal cost calculation (can be wired in proposal agent).

## Debt / follow-ups

- Add phased delivery instructions to SynthesisAgent and ProposalAgent SYSTEM_PROMPT.
- Use hourly_rate in proposal to set estimated_cost_gbp per phase.
- Stage-by-stage progress and summary output formatting.

## Reviewer checklist

- [ ] Run `pytest tests/test_contracts.py -k proposal -v`.
- [ ] `python main.py --input ./workspace/sample_transcript.txt --client "Acme" --quality premium` runs with ensemble.
- [ ] `python main.py --hourly-rate 200` passes 200 to run_factory.
