# Autonomous Build Instructions for Cursor

**Mission:** Implement Phases 11-15 of the Meta-Factory roadmap autonomously over 6-8 hours.

**Context:** You are building internal tooling for a consultancy. The system generates software proposals from transcripts/codebases. Phases 1-10 are complete. Your job is to make it production-ready for daily team use.

**Critical Rules:**
1. **Follow the plan exactly** - Read `FORGE-STREAM-PLAN.md` phases 11-15 before starting
2. **Test after each phase** - If tests fail, fix them before moving on
3. **Commit after each phase** - Use descriptive commit messages
4. **Document blockers** - If stuck >15 minutes, document the issue in `BLOCKERS.md` and move on
5. **Preserve existing code** - Only add/modify files listed in the phase spec

---

## Pre-Flight Checklist

Before starting, verify:

```bash
# 1. Check current state
pwd  # Should be in /Users/adam.sroka/Documents/CODE/meta-factory
git status  # Should be clean or on a feature branch

# 2. Verify Python environment
python3 --version  # Should be 3.9+
source .venv/bin/activate || python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run existing tests to establish baseline
pytest -v 2>&1 | tee test_baseline.log
# Expected: 121/122 passing (1 RAG test may fail without RAGFlow)

# 4. Check API key is set
echo $OPENAI_API_KEY | head -c 10
# Should show: sk-proj-XX... (or another provider key)

# 5. Create feature branch
git checkout -b phases-11-15-autonomous-build
```

If any of these fail, STOP and document in `BLOCKERS.md`.

---

## Phase 11: Production Reliability & Observability

**Objective:** Ship v1.0 that works reliably. Add structured logging, fix tests, simplify config.

**Duration Estimate:** 90 minutes

### Step 11.1: Install structlog and update requirements

```bash
# Add to requirements.txt (if not present)
echo "structlog>=23.1.0" >> requirements.txt
pip install structlog
```

### Step 11.2: Create structured logging infrastructure

**File:** `utils/logging.py` (create new file)

Read the specification in `FORGE-STREAM-PLAN.md` lines 1466-1505.

Implementation checklist:
- [ ] Create `utils/` directory if it doesn't exist
- [ ] Create `utils/__init__.py`
- [ ] Implement `setup_logging()` function with:
  - Console handler (INFO+ level)
  - File handler (DEBUG+ level, saves to `outputs/{run_id}/run.log`)
  - JSON renderer for file, Console renderer for terminal
- [ ] Export `structlog.get_logger()` wrapper

**Verify:**
```python
from utils.logging import setup_logging
from pathlib import Path
logger = setup_logging("test_run", Path("outputs/test_run"), verbose=True)
logger.info("test_message", foo="bar")
# Should print to console and write to outputs/test_run/run.log
```

### Step 11.3: Add logging to BaseAgent

**File:** `agents/base_agent.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 1507-1534

Add logging to:
- `run()` method start (log agent, tier, model)
- `run()` method success (log tokens, cost, retries)
- `run()` method failure (log error)

**Verify:**
```bash
# Run a simple agent (should see structured logs)
python3 -c "
from agents import DiscoveryAgent
from contracts import DiscoveryInput
agent = DiscoveryAgent()
# Mock run - logs should appear
print('Logging test passed')
"
```

### Step 11.4: Add logging to BaseSwarm

**File:** `swarms/base_swarm.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 1536-1565

Add logging to:
- `_run_stage_with_retry()` (log stage start, complete, fail)
- Include stage name, duration, cost_exceeded flag

### Step 11.5: Initialize logging in main.py

**File:** `main.py` (modify existing)

Add near top of `main()` function:
```python
from utils.logging import setup_logging

# After run_id is determined
logger = setup_logging(run_id, Path("outputs") / run_id, verbose=verbose)
logger.info("meta_factory_started",
            client=client_name,
            quality=quality,
            mode=mode)
```

### Step 11.6: Fix failing test

**File:** `tests/test_rag_client.py` (modify existing)

Add marker to skip without RAGFlow:
```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("META_FACTORY_RAGFLOW_API_KEY"),
    reason="RAGFlow not configured"
)
def test_client_requires_api_key_for_availability():
    ...
```

### Step 11.7: Add pytest.ini with markers

**File:** `pytest.ini` (create new)

```ini
[pytest]
markers =
    integration: Integration tests requiring external services
    rag: Tests requiring RAGFlow
    slow: Tests that take >5s
```

### Step 11.8: Create .env.example

**File:** `.env.example` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 1609-1624

### Step 11.9: Update README.md with 5-minute quickstart

**File:** `README.md` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 1626-1657

Replace or add a "5-Minute Quickstart" section at the top.

### Step 11.10: Add cost summary table to output

**File:** `orchestrator/cost_controller.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 1661-1707

Add:
- `StageMetrics` model
- `record_stage()` method
- `generate_summary()` method that returns Rich table

**File:** `main.py` (modify existing)

After run completes, call `cost_controller.generate_summary()` and print.

### Step 11.11: Test Phase 11

```bash
# 1. Run tests
pytest -v
# Expected: 122/122 passing (RAG test now skipped)

# 2. Test logging
python main.py --input workspace/sample_transcript.txt --client "Phase11Test" --quality standard
# Verify:
# - outputs/run_*/run.log exists with JSON logs
# - Cost summary table prints at end
# - Run completes successfully

# 3. Test fresh setup (simulate new user)
cd /tmp
git clone /Users/adam.sroka/Documents/CODE/meta-factory meta-factory-test
cd meta-factory-test
export OPENAI_API_KEY=$OPENAI_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --input workspace/sample_transcript.txt --client Test
# Should complete in <10 minutes
```

### Step 11.12: Commit Phase 11

```bash
git add -A
git commit -m "Phase 11: Production Reliability

- Add structured logging (structlog) to BaseAgent and BaseSwarm
- Fix RAG test with skipif marker
- Add pytest.ini with markers
- Create .env.example for quick setup
- Update README with 5-minute quickstart
- Add cost/timing summary table to output
- All tests passing (122/122)

Acceptance: New user can generate first proposal in <10 minutes"
```

If anything fails, document in `BLOCKERS.md` and continue to Phase 12.

---

## Phase 12: Proposal Iteration & Diff Support

**Objective:** Enable rapid iteration. Compare proposals, show diffs, support variations.

**Duration Estimate:** 120 minutes

### Step 12.1: Create diff engine

**File:** `utils/proposal_diff.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 1784-1894

Implement:
- `PhaseDiff` model
- `ProposalDiff` model with `to_markdown()` method
- `generate_proposal_diff()` function

**Key logic:**
- Compare phases by name
- Calculate deltas (hours, cost, timeline)
- Track added/removed phases
- Track changed phases with milestone diffs

### Step 12.2: Add CLI flags for baseline/compare

**File:** `main.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 1898-1968

Add options:
- `--baseline RUN_ID` - Compare against this run
- `--compare-only` - Don't run pipeline, just generate diff
- `--variation NAME` - Label this run as a variation

Wire up logic:
1. If `--baseline` set, load baseline artifacts
2. Run new proposal (or skip if `--compare-only`)
3. Generate diff using `generate_proposal_diff()`
4. Save diff to `outputs/{new_run}/diff_vs_{baseline}.md`
5. Print diff to console

### Step 12.3: Add variation to metadata

**File:** `orchestrator/engagement_manager.py` or wherever `run_metadata.json` is written

Add `variation` and `baseline` fields to metadata JSON.

### Step 12.4: Create variation comparison script

**File:** `scripts/compare_variations.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 1970-2036

Implement:
- Load all runs that have same baseline
- Extract key metrics (hours, cost, timeline)
- Display as Rich table

### Step 12.5: Test Phase 12

```bash
# 1. Generate baseline
python main.py --input workspace/sample_transcript.txt --client "Acme" --quality standard
# Note run_id (e.g., run_20260219_...)

# 2. Create modified transcript
cp workspace/sample_transcript.txt workspace/sample_transcript_minimal.txt
# (Manually edit to remove some features)

# 3. Generate variation
python main.py --input workspace/sample_transcript_minimal.txt --client "Acme" --baseline run_001 --variation minimal

# 4. Check diff
cat outputs/run_002/diff_vs_run_001.md
# Should show:
# - Hours delta
# - Cost delta
# - Phases added/removed
# - Milestone changes

# 5. Compare variations
python scripts/compare_variations.py run_001
# Should show table of all variations
```

### Step 12.6: Commit Phase 12

```bash
git add -A
git commit -m "Phase 12: Proposal Iteration & Diff Support

- Add utils/proposal_diff.py with ProposalDiff engine
- Add --baseline, --compare-only, --variation flags to main.py
- Add variation field to run_metadata.json
- Create scripts/compare_variations.py
- Enable rapid iteration workflow (baseline → variations → diff)

Acceptance: Can generate 3 variations and compare side-by-side"
```

---

## Phase 13: Prompt Gallery & A/B Testing

**Objective:** Make prompts editable by non-coders. Enable A/B testing.

**Duration Estimate:** 150 minutes

### Step 13.1: Create prompts directory structure

```bash
mkdir -p agents/prompts
touch agents/prompts/__init__.py
```

### Step 13.2: Extract prompts to YAML

**Files:** Create these new files in `agents/prompts/`:
- `discovery.yaml`
- `architect.yaml`
- `estimator.yaml`
- `synthesis.yaml`
- `proposal.yaml`
- `critic.yaml`
- `miner.yaml`

Read spec: `FORGE-STREAM-PLAN.md` lines 2086-2166

For each agent:
1. Find existing `SYSTEM_PROMPT` in agent file (e.g., `agents/discovery_agent.py`)
2. Extract to YAML format:
   ```yaml
   version: "1.0"
   system_prompt: |
     [paste existing prompt here]

   variants:
     default:
       system_prompt: |
         [same as above]
     concise:
       system_prompt: |
         [shorter version - you can create this]

   examples: []
   metadata:
     author: "Adam (via Cursor)"
     last_updated: "2026-02-19"
     tags: []
   ```

### Step 13.3: Create prompt loader

**File:** `agents/prompt_loader.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2170-2230

Implement:
- `PromptFile` model (version, system_prompt, variants, examples, metadata)
- `PromptLoader` class with `load()` and `list_variants()` methods
- Singleton `get_prompt_loader()` function

### Step 13.4: Update BaseAgent to use prompt loader

**File:** `agents/base_agent.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 2232-2258

Changes:
- Make `system_prompt` parameter optional in `__init__`
- Add `prompt_variant` parameter (default: "default")
- If `system_prompt` is None, load from YAML using `prompt_loader.load(role, variant)`

### Step 13.5: Update all agent constructors

**Files:** Modify these files:
- `agents/discovery_agent.py`
- `agents/architect_agent.py`
- `agents/estimator_agent.py`
- `agents/synthesis_agent.py`
- `agents/proposal_agent.py`
- `agents/critic_agent.py`
- `agents/miner_agent.py`

For each:
1. Remove `SYSTEM_PROMPT` class attribute (it's now in YAML)
2. Remove `system_prompt=self.SYSTEM_PROMPT` from `super().__init__` call
3. Add `prompt_variant="default"` parameter to constructor
4. Pass `prompt_variant=prompt_variant` to `super().__init__`

### Step 13.6: Add CLI flag for prompt variant

**File:** `main.py` (modify existing)

Add:
```python
@click.option(
    "--prompt-variant",
    default="default",
    help="Prompt variant to use (default, concise, experimental)"
)
```

Thread through to swarms and agents.

### Step 13.7: Create A/B test utilities

**File:** `utils/ab_test.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2270-2350

Implement:
- `VariantResult` model
- `ABTestReport` model with `to_markdown()` method
- `run_ab_test()` function

### Step 13.8: Create A/B test script

**File:** `scripts/ab_test_prompts.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2352-2389

CLI that:
1. Takes `--agent`, `--variants`, `--input`, `--client`
2. Runs `run_ab_test()`
3. Prints report
4. Saves to `outputs/ab_test_{agent}.md`

### Step 13.9: Test Phase 13

```bash
# 1. Verify prompt loading
python3 -c "
from agents.prompt_loader import get_prompt_loader
loader = get_prompt_loader()
prompt = loader.load('discovery', 'default')
print(f'Loaded prompt: {len(prompt)} chars')
variants = loader.list_variants('discovery')
print(f'Variants: {variants}')
"

# 2. Test variant selection
python main.py --input workspace/sample_transcript.txt --client Test --prompt-variant concise
# Should complete successfully

# 3. Test A/B testing
python scripts/ab_test_prompts.py --agent discovery --variants default,concise --input workspace/sample_transcript.txt --client Test
# Should generate report in outputs/ab_test_discovery.md
```

### Step 13.10: Commit Phase 13

```bash
git add -A
git commit -m "Phase 13: Prompt Gallery & A/B Testing

- Extract all agent prompts to YAML (agents/prompts/*.yaml)
- Create prompt_loader.py with variant support
- Update BaseAgent to load prompts from YAML
- Add --prompt-variant CLI flag
- Create utils/ab_test.py and scripts/ab_test_prompts.py
- Enable non-coders to edit prompts and A/B test improvements

Acceptance: Non-technical user can edit discovery.yaml and see results"
```

---

## Phase 14: Reference Class Forecasting

**Objective:** Use historical data to improve estimates. System learns from completed projects.

**Duration Estimate:** 120 minutes

### Step 14.1: Create outcome contracts

**File:** `contracts/outcomes.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2438-2550

Implement:
- `PhaseOutcome` model (estimated vs actual for a single phase)
- `ProjectOutcome` model (full project with metadata)
- `HistoricalDatabase` model with methods:
  - `add_project()`
  - `find_similar()`
  - `get_correction_factor()`

### Step 14.2: Create historical database utilities

**File:** `utils/historical_db.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2554-2594

Implement:
- `load_historical_db()` - Load from `data/historical_projects.json`
- `save_historical_db()` - Save to JSON
- `add_outcome()` - Add project and save individual file

Create `data/` directory:
```bash
mkdir -p data/outcomes
```

### Step 14.3: Create reference-adjusted estimator

**File:** `agents/reference_estimator.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2596-2674

Implement:
- `ReferenceEstimator` class that extends `EstimatorAgent`
- `estimate()` method that:
  1. Gets base estimate from LLM
  2. Loads correction factor from historical DB
  3. Applies correction to all tasks
  4. Recalculates totals and confidence intervals

### Step 14.4: Create outcome recording script

**File:** `scripts/record_outcome.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2678-2778

Interactive CLI that:
1. Loads original proposal from run_id
2. Prompts for actual hours per phase
3. Calculates accuracy ratios
4. Saves to historical database

### Step 14.5: Add CLI flag for reference forecasting

**File:** `main.py` (modify existing)

Add:
```python
@click.option(
    "--use-reference-forecast",
    is_flag=True,
    help="Apply reference class forecasting corrections from historical data"
)
```

Wire into swarms: when True, use `ReferenceEstimator` instead of `EstimatorAgent`.

### Step 14.6: Create forecast report script

**File:** `scripts/forecast_report.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2788-2850

Shows:
- Total projects in database
- Accuracy by mode (greenfield/brownfield/greyfield)
- Accuracy by phase type (poc/mvp/v1)
- Recent projects

### Step 14.7: Test Phase 14

```bash
# 1. Create sample historical data
mkdir -p data/outcomes
cat > data/historical_projects.json << 'EOF'
{
  "projects": [
    {
      "run_id": "sample_001",
      "client_name": "TestCo",
      "project_name": "Sample Project",
      "mode": "greenfield",
      "quality": "standard",
      "domain": "logistics",
      "project_type": "mobile-app",
      "team_size": 3,
      "phases": [
        {
          "phase_name": "POC",
          "phase_type": "poc",
          "estimated_hours": 80,
          "actual_hours": 100,
          "accuracy_ratio": 1.25,
          "estimated_weeks": 4,
          "actual_weeks": 5
        }
      ],
      "total_estimated_hours": 80,
      "total_actual_hours": 100,
      "overall_accuracy_ratio": 1.25,
      "proposal_generated_date": "2026-01-15T10:00:00",
      "project_completed_date": "2026-02-15T17:00:00",
      "lessons_learned": "Underestimated integration complexity"
    }
  ]
}
EOF

# 2. Test reference estimator
python main.py --input workspace/sample_transcript.txt --client Test --use-reference-forecast
# Should apply 1.25x correction

# 3. Test forecast report
python scripts/forecast_report.py
# Should show the sample project

# 4. Test outcome recording (interactive - may skip in autonomous mode)
# python scripts/record_outcome.py --run-id run_XXX --domain logistics --project-type mobile-app --team-size 3
```

### Step 14.8: Commit Phase 14

```bash
git add -A
git commit -m "Phase 14: Reference Class Forecasting

- Add contracts/outcomes.py with ProjectOutcome and HistoricalDatabase
- Create utils/historical_db.py for data management
- Implement ReferenceEstimator with historical corrections
- Add scripts/record_outcome.py for capturing actuals
- Add scripts/forecast_report.py to show accuracy trends
- Add --use-reference-forecast flag
- Enable learning from completed projects

Acceptance: After 5 projects, estimates auto-adjust based on historical accuracy"
```

---

## Phase 15: Production Optimization & Polish

**Objective:** Make it fast, reliable, pleasant. Cost prediction, streaming, parallel execution.

**Duration Estimate:** 150 minutes

### Step 15.1: Create cost predictor

**File:** `utils/cost_predictor.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 2976-3030

Implement:
- `COST_ESTIMATES` dict with historical averages
- `estimate_cost_and_time()` function

### Step 15.2: Add --estimate-only flag

**File:** `main.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 3032-3061

Add flag and logic:
1. If `--estimate-only`, show prediction
2. Prompt user to proceed
3. If no, exit

### Step 15.3: Add streaming progress to BaseSwarm

**File:** `swarms/base_swarm.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 3067-3093

Add:
- `progress_callback` parameter to `__init__`
- `_emit_progress()` method
- Call `_emit_progress()` at stage start/complete/fail

### Step 15.4: Update main.py with live progress table

**File:** `main.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 3095-3143

Use `rich.live.Live` to show real-time progress table.

### Step 15.5: Parallel ensemble estimation

**File:** `swarms/greenfield.py` (modify existing)

Read spec: `FORGE-STREAM-PLAN.md` lines 3149-3223

Update `_run_estimation()` to:
- Use `ThreadPoolExecutor` when `ensemble=True`
- Run optimist/pessimist/realist in parallel
- Check cost after all three complete

### Step 15.6: Create friendly error handler

**File:** `utils/error_handler.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 3229-3305

Implement `handle_error()` that detects common errors and shows friendly messages:
- No LLM providers configured
- Invalid API key (401)
- Budget exceeded
- Generic errors (with traceback)

### Step 15.7: Add error handling to main.py

**File:** `main.py` (modify existing)

Wrap `main()` body in try/except, call `handle_error()` on exception.

### Step 15.8: (Optional) Add caching

**File:** `utils/cache.py` (create new)

Read spec: `FORGE-STREAM-PLAN.md` lines 3309-3351

Implement:
- `compute_cache_key()` - Hash inputs
- `check_cache()` - Load cached result
- `save_cache()` - Save result

Add `--no-cache` flag to bypass.

**Note:** This is optional. If time is running short, skip caching.

### Step 15.9: Test Phase 15

```bash
# 1. Test cost prediction
python main.py --input workspace/sample_transcript.txt --client Test --estimate-only
# Should show estimate and prompt

# 2. Test streaming progress (if implemented)
python main.py --input workspace/sample_transcript.txt --client Test --quality premium
# Should show live-updating table

# 3. Test error handling
unset OPENAI_API_KEY
python main.py --input workspace/sample_transcript.txt --client Test
# Should show friendly "No API key" message

export OPENAI_API_KEY=invalid-key
python main.py --input workspace/sample_transcript.txt --client Test
# Should show friendly "Invalid API key" message

# Restore key
export OPENAI_API_KEY=[your real key]

# 4. Test parallel execution (if ensemble implemented)
time python main.py --input workspace/sample_transcript.txt --client Test --quality premium
# Should be faster than 3x sequential
```

### Step 15.10: Commit Phase 15

```bash
git add -A
git commit -m "Phase 15: Production Optimization & Polish

- Add utils/cost_predictor.py and --estimate-only flag
- Add streaming progress with live table (rich.live.Live)
- Parallelize ensemble estimation (3x speedup)
- Add utils/error_handler.py with friendly error messages
- (Optional) Add caching for instant re-runs
- Improve UX: faster, more informative, better errors

Acceptance: Standard <3min, Premium <8min, all errors actionable"
```

---

## Final Steps

### Run Full Test Suite

```bash
# 1. All unit tests
pytest -v
# Expected: 122/122 passing (or close, document any failures)

# 2. End-to-end smoke test
python main.py --input workspace/sample_transcript.txt --client "E2E-Test" --quality standard
# Should complete in <5 minutes

# 3. Premium quality smoke test
python main.py --input workspace/sample_transcript.txt --client "E2E-Premium" --quality premium
# Should complete in <10 minutes with ensemble

# 4. Diff workflow test
python main.py --input workspace/sample_transcript.txt --client "Diff-Baseline"
BASELINE_ID=$(ls -t outputs/ | head -1)
python main.py --input workspace/sample_transcript.txt --client "Diff-Variation" --baseline $BASELINE_ID --variation minimal
cat outputs/*/diff_vs_*.md
# Should show diff

# 5. Prompt variant test
python main.py --input workspace/sample_transcript.txt --client "Variant-Test" --prompt-variant concise
# Should complete
```

### Create Summary Document

**File:** `PHASES-11-15-IMPLEMENTATION-LOG.md` (create new)

```markdown
# Phases 11-15 Implementation Log

**Completed:** [Date/Time]
**Duration:** [X hours]

## Phase 11: Production Reliability ✅
- Status: [Complete/Partial/Blocked]
- Key changes:
  - Added structlog with JSON logging
  - Fixed RAG test with skipif
  - Updated README with quickstart
  - Cost summary table working
- Tests: [X/122 passing]
- Blockers: [None / list any]

## Phase 12: Iteration & Diff ✅
- Status: [Complete/Partial/Blocked]
- Key changes:
  - Diff engine implemented
  - --baseline, --variation flags working
  - compare_variations.py script working
- Tests: [Manual verification / unit tests]
- Blockers: [None / list any]

## Phase 13: Prompt Gallery ✅
- Status: [Complete/Partial/Blocked]
- Key changes:
  - All prompts extracted to YAML
  - Prompt loader working
  - A/B test script implemented
- Tests: [Prompt loading verified]
- Blockers: [None / list any]

## Phase 14: Reference Forecasting ✅
- Status: [Complete/Partial/Blocked]
- Key changes:
  - Historical database implemented
  - ReferenceEstimator working
  - record_outcome.py script created
- Tests: [Mock historical data verified]
- Blockers: [None / list any]

## Phase 15: Optimization ✅
- Status: [Complete/Partial/Blocked]
- Key changes:
  - Cost prediction working
  - Streaming progress (if implemented)
  - Parallel ensemble (if implemented)
  - Error handling improved
- Tests: [Speed improvements verified]
- Blockers: [None / list any]

## Overall Status
- Tests passing: [X/122]
- E2E verification: [Pass/Fail]
- Known issues: [list]
- Recommended next steps: [list]
```

### Final Commit and Tag

```bash
# Commit implementation log
git add PHASES-11-15-IMPLEMENTATION-LOG.md
git commit -m "Implementation log for phases 11-15"

# Merge to main (if all tests pass)
git checkout main
git merge phases-11-15-autonomous-build

# Tag as v1.1 (or appropriate version)
git tag -a v1.1-internal-tooling -m "Phases 11-15: Internal consultancy tooling complete
- Production reliability (logging, tests, config)
- Iteration support (diff, variations)
- Prompt gallery (YAML, A/B testing)
- Reference forecasting (historical learning)
- Production polish (speed, UX, errors)"

# Push
git push origin main --tags
```

---

## Error Handling Protocol

If you encounter errors:

### 1. Dependency errors
```bash
# Update requirements if needed
pip install --upgrade -r requirements.txt

# Document any new dependencies added
echo "newpackage>=1.0.0  # Added for Phase X feature" >> requirements.txt
```

### 2. Test failures
- Try to fix within 15 minutes
- If can't fix, document in `BLOCKERS.md`:
  ```markdown
  ## Phase X: [Title]

  **Test failing:** `test_name` in `file.py`
  **Error:** [paste error]
  **Attempted fixes:** [what you tried]
  **Impact:** [can continue / must fix before next phase]
  ```
- Continue to next phase if not blocking

### 3. API errors
- Verify API key is set
- Check API key is valid (not expired)
- Document any rate limits hit
- Use mock data if API unavailable

### 4. File not found
- Double-check path in FORGE-STREAM-PLAN.md
- File may have been moved in previous phases
- Check git history: `git log --all --full-history -- path/to/file`

### 5. Merge conflicts
- Shouldn't happen on feature branch
- If they do, resolve in favor of new code
- Document in implementation log

---

## Success Criteria

At completion, verify:

✅ **Phase 11:**
- [ ] pytest passes 122/122 (or documents failures)
- [ ] New user can run first proposal in <10 minutes
- [ ] Logs exist as JSON in outputs/run_*/run.log
- [ ] Cost summary table prints

✅ **Phase 12:**
- [ ] --baseline flag generates diff
- [ ] Diff shows ±cost, ±hours, phases changed
- [ ] compare_variations.py works

✅ **Phase 13:**
- [ ] All prompts in agents/prompts/*.yaml
- [ ] --prompt-variant selects variants
- [ ] ab_test_prompts.py runs

✅ **Phase 14:**
- [ ] Historical database loads/saves
- [ ] ReferenceEstimator applies corrections
- [ ] record_outcome.py prompts for actuals

✅ **Phase 15:**
- [ ] --estimate-only shows prediction
- [ ] (Optional) Streaming progress works
- [ ] (Optional) Parallel ensemble speeds up premium
- [ ] Error messages are friendly

✅ **Overall:**
- [ ] All commits have descriptive messages
- [ ] Implementation log is complete
- [ ] Known issues are documented
- [ ] E2E test passes

---

## Time Estimates

| Phase | Estimated Duration | Checkpoints |
|-------|-------------------|-------------|
| **Pre-flight** | 10 min | Environment verified |
| **Phase 11** | 90 min | Tests pass, logging works |
| **Phase 12** | 120 min | Diff generates correctly |
| **Phase 13** | 150 min | Prompts load from YAML |
| **Phase 14** | 120 min | Historical DB works |
| **Phase 15** | 150 min | Cost prediction works |
| **Testing & docs** | 60 min | All smoke tests pass |
| **Total** | ~11 hours | |

**Buffer:** If any phase takes >2x estimated, document blocker and move on.

---

## Final Notes

**You are autonomous.** Make reasonable decisions when:
- Minor implementation details aren't specified
- You find a better way to structure something
- Tests need adjusting due to changes

**Document everything.** If you skip something, say why. If you add something, say why.

**Test as you go.** Don't wait until the end to test everything.

**Commit frequently.** After each phase, commit with clear message.

**Good luck!** 🚀

When done, the user will review:
1. `git log --oneline` - commit history
2. `PHASES-11-15-IMPLEMENTATION-LOG.md` - what worked/failed
3. `pytest -v` - test results
4. E2E run - does it actually work?

**START WITH PRE-FLIGHT CHECKLIST, THEN PROCEED PHASE BY PHASE.**
