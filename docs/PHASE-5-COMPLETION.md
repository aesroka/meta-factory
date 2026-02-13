# Phase 5 Completion Note: Quality Gate (Tiered Critic Loop)

**Completed:** 2025-02-12

## What was done

- **5.1** CriticAgent tier routing: `self.model = model or "tier2"` so critics route through Router's tier2 models.
- **5.2** `BaseAgent.run(model: Optional[str] = None)` for one-shot model override.
- **5.3** Tier escalation in `run_with_critique()`: first retry same tier, second+ retry `model="tier3"`; metadata set/restored for cost logs.
- **5.4** Budget warning in `SwarmCostLogger` at 80% of `litellm.max_budget`; `cost_warning_threshold` in config.
- **5.5** `tests/test_quality_gate.py`: critic tier2, escalation on second retry, budget warning, no escalation when critic passes first time.

## E2E testing

- **Iteration 1:** Unit tests failed — `ConcreteSwarm` in tests was missing abstract methods `execute` and `mode_name`.
- **Iteration 2:** Implemented `mode_name` (property) and `execute()` on test `ConcreteSwarm`; all 5 tests pass.
- **E2E:** `python scripts/showcase_forge_stream.py --dry-run` and `python scripts/showcase_forge_stream.py -p openai --max-cost 2.0` both succeeded.

## Gotchas

- **BaseSwarm is ABC:** Any test swarm must implement `mode_name` and `execute()`, not just `run()`.
- **Metadata restore:** After escalated run we restore agent metadata to default tier so subsequent calls don’t keep `tier3`/`escalated` in logs.
- **Cost logger:** Budget warning uses hardcoded 0.8 to avoid importing config (circular import risk). Config has `cost_warning_threshold` for future use.

## Debt / follow-ups

- `_enrich_with_feedback` adds `previous_feedback` to input dict then `model_validate()` — if contracts don’t allow extra fields this can break; consider `extra="allow"` or a dedicated feedback field.
- Budget warning message could use `config.cost_warning_threshold` if we inject it or resolve circular import (e.g. lazy read in logger).

## Reviewer checklist

- [ ] Run `pytest tests/test_quality_gate.py -v`.
- [ ] Run `python scripts/showcase_forge_stream.py -p openai` and confirm cost logs show `tier:tier1` (Discovery), `tier:tier2` (Critic), `tier:tier3` (Architect/Estimator/Synthesis/Proposal).
- [ ] If a critic fails twice, third run should show escalated tier3 in logs.
