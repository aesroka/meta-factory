# v1.0 Launch Checklist

Use this as the acceptance checklist for Forge-Stream v1.0 (from FORGE-STREAM-PLAN Phase 10.6).

## Acceptance criteria

- [ ] `python main.py --input transcript.txt --client "X" --quality standard` produces a phased proposal (POC + MVP + V1) with PERT estimates and confidence intervals in under 5 minutes.
- [ ] `python main.py --input transcript.txt --client "X" --quality premium` produces a higher-quality proposal using hybrid context + ensemble estimation.
- [ ] Every proposal has at least 2 delivery phases (when prompts emit them). The first phase is ≤6 weeks. Each phase has success criteria and `can_stop_here` set correctly.
- [ ] The hybrid context mode produces a Dossier that can be reconciled (RAG + full-context); reconciliation contract and heuristic merge implemented.
- [ ] The ensemble estimation produces a range, not a point estimate, with correct PERT math (aggregator tests pass).
- [ ] All three swarm modes (greenfield, brownfield, greyfield) run successfully with optional dossier integration.
- [ ] Tier routing is correct: tier0 for Oracle, tier1 for extraction, tier2 for critics, tier3 for synthesis.
- [ ] Cost is tracked and reported accurately. `--hourly-rate` is passed through (proposal agent can use it for GBP estimates).
- [ ] `pytest` passes with no failures (excluding known flaky or env-dependent tests).
- [ ] A non-developer can read README.md and run their first engagement in under 10 minutes.
- [ ] The output for a small transcript (~5K tokens, £50K engagement) is a concise plan; proposal structure supports phased delivery.

## Phase completion notes

- **Phase 5:** Quality gate (critic tier2, escalation to tier3, budget warning). See docs/PHASE-5-COMPLETION.md.
- **Phase 6:** Hybrid context (tier0, context_mode, reconciliation). See docs/PHASE-6-COMPLETION.md.
- **Phase 7:** Ensemble estimation. See docs/PHASE-7-COMPLETION.md.
- **Phase 8:** Brownfield/Greyfield dossier integration. See docs/PHASE-8-COMPLETION.md.
- **Phase 9:** Phased delivery contracts and CLI (--quality, --hourly-rate). See docs/PHASE-9-COMPLETION.md.
- **Phase 10:** Dead code removal, README, launch checklist. See docs/PHASE-10-COMPLETION.md.

## Run before release

```bash
pytest -v
python main.py --list-providers
python scripts/showcase_forge_stream.py --dry-run
python main.py --input ./workspace/sample_transcript.txt --client "Acme" --quality standard
```
