# Phases 11-15: Internal Consultancy Tooling

**Updated:** 2026-02-19
**Purpose:** Post-v1.0 phases focused on making Meta-Factory production-ready for daily internal use

---

## Overview

These phases transform Meta-Factory from "technically complete" to "team loves using it." Focus is on:
- **Reliability** - It just works, every time
- **Speed** - Fast feedback loops for client iterations
- **Ease of use** - Non-coders can tweak prompts and understand output
- **Learning** - System gets better with each project

---

## Phase 11: Production Reliability & Observability ✅

**Goal:** Ship v1.0 that works reliably out of the box

**Key Changes:**
- Structured logging with `structlog` (filter by severity, aggregate costs, track timing)
- Fix failing test (mark RAG tests as optional)
- Simplify configuration (5-minute quickstart, clear error messages)
- Cost/timing summary table at end of run

**Success Criteria:**
- New team member can clone, set API key, generate first proposal in <10 minutes
- `pytest` passes 122/122 tests (or marks RAG as optional)
- Logs are machine-readable (JSON) for analysis
- Clear cost breakdown by stage

**Files Touched:**
- `utils/logging.py` (new)
- `agents/base_agent.py` (add logging)
- `swarms/base_swarm.py` (add logging)
- `main.py` (initialize logging, show summary table)
- `README.md` (5-minute quickstart)
- `.env.example` (minimal config template)
- `tests/test_rag_client.py` (mark as @pytest.mark.rag)
- `pytest.ini` (new markers)

---

## Phase 12: Proposal Iteration & Diff Support

**Goal:** Enable rapid iteration. Client says "cut feature X" → show exactly what changes.

**Key Changes:**
- `--baseline` flag to compare against previous run
- Diff engine shows changes in cost, timeline, phases, risks
- `--variation` flag for "minimal/standard/premium" scope options
- `scripts/compare_variations.py` to compare 3+ variations side-by-side

**Success Criteria:**
- Generate 3 variations of a proposal
- Diff shows: ±hours, ±cost, phases added/removed, milestones changed
- Client can choose which scope fits budget

**Files Touched:**
- `utils/proposal_diff.py` (new - diff engine)
- `main.py` (add --baseline, --variation, --compare-only flags)
- `scripts/compare_variations.py` (new - compare multiple variations)
- `run_metadata.json` (add variation field)
- `tests/test_proposal_diff.py` (new)

**Example Workflow:**
```bash
# Baseline
python main.py --input transcript.txt --client Acme

# Variation 1: minimal scope
python main.py --input transcript_minimal.txt --client Acme --baseline run_001 --variation minimal

# Variation 2: premium scope
python main.py --input transcript_premium.txt --client Acme --baseline run_001 --variation premium

# Compare all
python scripts/compare_variations.py run_001
```

---

## Phase 13: Prompt Gallery & A/B Testing

**Goal:** Make prompts editable by non-coders. Enable A/B testing to validate improvements.

**Key Changes:**
- Extract all agent prompts to YAML files (`agents/prompts/*.yaml`)
- Support variants (default, concise, experimental, etc.)
- `--prompt-variant` flag to select variant
- `scripts/ab_test_prompts.py` to compare variants objectively

**Success Criteria:**
- Non-technical consultant can edit `discovery.yaml`, add "detailed" variant
- Run with `--prompt-variant detailed`
- A/B test shows which variant produces better results (more pain points, higher confidence, etc.)

**Files Touched:**
- `agents/prompts/` (new directory with discovery.yaml, architect.yaml, etc.)
- `agents/prompt_loader.py` (new - YAML loader)
- `agents/base_agent.py` (use prompt loader)
- All agent files (remove hardcoded prompts)
- `main.py` (add --prompt-variant flag)
- `utils/ab_test.py` (new - A/B test runner)
- `scripts/ab_test_prompts.py` (new - CLI for A/B testing)
- `tests/test_prompt_loader.py` (new)

**Example Workflow:**
```bash
# Edit prompt
vim agents/prompts/discovery.yaml
# Add a "detailed" variant under variants:

# Test it
python main.py --input transcript.txt --client Acme --prompt-variant detailed

# A/B test
python scripts/ab_test_prompts.py --agent discovery --variants default,detailed --input workspace/sample_transcript.txt
# Generates report showing cost, duration, output quality for each variant
```

---

## Phase 14: Reference Class Forecasting

**Goal:** Use completed project data to improve estimates. The killer feature for consultancies.

**Key Changes:**
- `ProjectOutcome` contract to track estimated vs actual hours
- `scripts/record_outcome.py` to capture actuals after project completion
- Historical database (`data/historical_projects.json`)
- `ReferenceEstimator` agent that applies correction factors from historical data
- `scripts/forecast_report.py` to show accuracy trends

**Success Criteria:**
- After 5 completed projects with 30% overrun (1.3x), new estimates automatically adjust by 1.3x
- Forecast report shows accuracy trends by mode (greenfield/brownfield/greyfield)
- System gets more accurate over time

**Files Touched:**
- `contracts/outcomes.py` (new - ProjectOutcome, HistoricalDatabase)
- `utils/historical_db.py` (new - load/save database)
- `agents/reference_estimator.py` (new - estimator with corrections)
- `scripts/record_outcome.py` (new - interactive outcome capture)
- `scripts/forecast_report.py` (new - show accuracy trends)
- `main.py` (add --use-reference-forecast flag)
- `data/` (new directory for historical data)
- `tests/test_reference_estimator.py` (new)

**Example Workflow:**
```bash
# 1. Generate proposal
python main.py --input transcript.txt --client Acme
# Proposal: 120 hours

# 2. Project completes, record actual
python scripts/record_outcome.py --run-id run_001 --domain logistics --project-type mobile-app --team-size 3
# Interactive: Enter actual hours (180), actual weeks (16), notes

# 3. Check database
python scripts/forecast_report.py
# Shows: 1 project, accuracy 1.5x (actual was 50% over)

# 4. Generate new proposal with correction
python main.py --input transcript2.txt --client TechCo --use-reference-forecast
# New estimate: 120h base * 1.5x correction = 180h
```

**Why This Matters:**
- Kahneman's "Outside View" - historical data beats expert opinion
- After 10+ projects, system estimates better than humans
- Consultancy-specific learning (your team, your clients, your patterns)

---

## Phase 15: Production Optimization & Polish

**Goal:** Make it fast, reliable, and pleasant to use daily.

**Key Changes:**
- Cost/time prediction before running (`--estimate-only`)
- Streaming progress updates (live table showing stage-by-stage progress)
- Parallel execution for ensemble estimation (3x speedup)
- Friendly error messages with suggestions
- Optional caching (instant re-run of same transcript)

**Success Criteria:**
- Cost prediction within 20% of actual
- Premium quality with ensemble completes in <50% of sequential time
- All errors show user-friendly messages with actionable fixes
- Cached run returns in <1 second

**Files Touched:**
- `utils/cost_predictor.py` (new - predict before running)
- `main.py` (add --estimate-only flag, streaming progress, error handling)
- `swarms/greenfield.py` (parallel ensemble estimation)
- `utils/error_handler.py` (new - friendly errors)
- `utils/cache.py` (new - optional caching)
- `tests/test_cost_predictor.py` (new)
- `tests/test_parallel_estimation.py` (new)

**User Experience Improvements:**

**Before (Phase 10):**
```
$ python main.py --input transcript.txt --client Acme
Processing... (spinner for 3 minutes)
Done! Cost: $1.23, Duration: 183s
```

**After (Phase 15):**
```
$ python main.py --input transcript.txt --client Acme --estimate-only

Estimated Cost & Duration
  Quality: standard
  Input size: 12,453 characters

  Cost: $0.80 - $3.00
  Duration: 2-5 minutes

Proceed with run? [Y/n] y

Meta-Factory Progress
┌─────────────┬──────────┬──────────┬─────────┐
│ Stage       │ Status   │ Duration │ Cost    │
├─────────────┼──────────┼──────────┼─────────┤
│ Discovery   │ ⏳ started│ -        │ -       │
│ Discovery   │ ✅ completed│ 12s   │ $0.082  │
│ Architecture│ ⏳ started│ -        │ -       │
│ Architecture│ ✅ completed│ 18s   │ $0.154  │
│ Estimation  │ ⏳ started│ -        │ -       │
│ Estimation  │ ✅ completed│ 25s   │ $0.213  │
│ Synthesis   │ ⏳ started│ -        │ -       │
│ Synthesis   │ ✅ completed│ 10s   │ $0.098  │
│ Proposal    │ ⏳ started│ -        │ -       │
│ Proposal    │ ✅ completed│ 15s   │ $0.145  │
└─────────────┴──────────┴──────────┴─────────┘

✅ Proposal generated!
   Total: $0.69, 80s, 5 stages
```

---

## Priority Recommendations

**Must Have (Launch Blockers):**
1. **Phase 11** - Can't ship without reliable logging and simplified setup
2. **Phase 12** - Iteration is core workflow, clients always ask "what if?"

**Should Have (High Value):**
3. **Phase 13** - Team wants to improve prompts but doesn't want to edit Python
4. **Phase 14** - Reference forecasting is the competitive advantage

**Nice to Have (Polish):**
5. **Phase 15** - Makes it faster and more pleasant, but not essential for v1.0

**Suggested Order:**
- Week 1-2: Phase 11 (get v1.0 stable)
- Week 3-4: Phase 12 (enable iteration workflow)
- Week 5-6: Phase 13 (make prompts editable)
- Month 2+: Phase 14 (after you have 5+ completed projects to learn from)
- Month 3+: Phase 15 (polish and optimize)

---

## Implementation Notes for Cursor

**General Guidance:**
- Each phase is designed to be ~1-2 weeks for a single developer
- Test files are specified for each phase
- File paths are explicit (not "somewhere in the codebase")
- Examples show actual usage patterns

**When implementing:**
1. Read the phase acceptance criteria first
2. Create the new files listed under "Files Touched"
3. Write tests before implementation (TDD)
4. Run manual workflow example to verify
5. Update docs (README, etc.) as specified

**Code Style:**
- Follow existing patterns (Pydantic contracts, BaseAgent inheritance, etc.)
- Add structured logging to new features
- Use type hints
- Keep functions small (<50 lines)
- Prefer composition over inheritance

**Testing:**
- Unit tests for business logic
- Integration tests for workflows
- Manual smoke tests for UX features
- Mark external-dependency tests with `@pytest.mark.integration`

---

## Success Metrics

**After Phase 11:**
- ✅ Team can run first proposal in <10 minutes
- ✅ Zero setup failures on fresh clone
- ✅ All tests pass or are properly marked

**After Phase 12:**
- ✅ Can generate 3 variations in <15 minutes
- ✅ Diff report shows clear cost/scope trade-offs
- ✅ Client chooses variation without consultant doing math

**After Phase 13:**
- ✅ Non-coder edits prompt and sees results
- ✅ A/B test shows objective improvement
- ✅ Team iterates on prompts weekly

**After Phase 14:**
- ✅ Estimates improve by 20% after 10 projects
- ✅ Forecast report shows trend toward 1.0x accuracy
- ✅ Reference corrections applied automatically

**After Phase 15:**
- ✅ Standard quality completes in <3 minutes
- ✅ Premium quality completes in <8 minutes (3x parallel speedup)
- ✅ Zero cryptic errors, all messages actionable
- ✅ Cached runs return in <2 seconds

---

## Questions?

If you need clarification on any phase, check:
1. The detailed phase spec in `FORGE-STREAM-PLAN.md`
2. Existing implementation patterns in the codebase
3. Tests for similar features

Each phase is self-contained and can be implemented independently (though order matters for dependencies).
