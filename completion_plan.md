# Meta-Factory Completion Plan (v2 — post Phase 15 review)

**Date:** 2026-02-28
**Author:** AdaL (project review — second pass)
**Target:** Cursor coding agent swarm
**Working directory:** `/Users/adam.sroka/Documents/CODE/meta-factory`
**Branch policy:** All work on `main`. Commit after each task with a conventional commit message.

---

## TL;DR

Most of the previous 12-task plan is **already done** (integration tests, progress callback, README v1.0 section). This revision documents current state, then adds a new set of tasks covering **real bugs found in this review**, dead code cleanup, and outstanding P3 housekeeping.

**Do NOT skip the P1 bugs.** They cause silent failures on Brownfield/Greyfield runs that produce wrong cost data and lose the retry safety net entirely.

| Priority | Focus | Tasks |
|----------|--------|--------|
| **P1** | Real bugs — fix before next client run | 1–5 |
| **P2** | Dead code, consistency, minor bugs | 6–10 |
| **P3** | Housekeeping & docs | 11–14 |

**Rough effort:** ~4–8 hours. P1 alone is ~2–3 hours.

---

## Previous Plan Status (as of this review)

| Old Task | Description | Status |
|----------|-------------|--------|
| Task 1 | E2E smoke test | ⚠️ Verify — run `scripts/smoke_test.sh` |
| Task 2 | Log file handle cleanup | ⚠️ Verify `utils/logging.py` |
| Task 3 | Dual cost system | ⚠️ Verify `run_metadata.json` has real cost |
| Task 4 | CI smoke script | `scripts/smoke_test.sh` exists — check it's runnable |
| Task 5 | Greenfield integration test | ✅ `tests/integration/test_greenfield_e2e.py` exists |
| Task 6 | Brownfield integration test | ✅ `tests/integration/test_brownfield_e2e.py` exists |
| Task 7 | Greyfield integration test | ✅ `tests/integration/test_greyfield_e2e.py` exists |
| Task 8 | Progress streaming callback | ✅ `BaseSwarm._emit_progress` implemented |
| Task 9 | Seed historical data | ⚠️ Verify `data/historical_projects.json` has records |
| Task 10 | Branch cleanup (phases-11-15) | ⚠️ Verify with `git branch -a` |
| Task 11 | Hybrid/reference forecasting docs | ⚠️ Check `docs/USAGE.md` |
| Task 12 | README v1.0 section | ✅ Present in README.md |

---

## Environment Setup (run once)

```bash
cd /Users/adam.sroka/Documents/CODE/meta-factory
source .venv/bin/activate    # preferred; or: source venv/bin/activate
pip install -r requirements.txt
python -c "from config import settings; print('Settings OK')"
```

---

# PRIORITY 1 — Real Bugs (Fix Before Any Client Run)

---

## Task 1: Port `_run_stage_with_retry` to BrownfieldSwarm and GreyfieldSwarm

**Why this matters:** `GreenfieldSwarm` wraps every stage in `_run_stage_with_retry`, which:
- Records stage **timing and cost** to `CostController` (the cost summary table is populated here)
- **Retries once** on transient LLM/network failures
- Emits `progress_callback` events with `started`/`completed`/`failed`

`BrownfieldSwarm` and `GreyfieldSwarm` call their `_run_*` methods directly with only a manual `_emit_progress("...", "started")` call and **no completion event, no cost recording, no retry**. This means:

- Brownfield/Greyfield runs show **empty cost summary tables** — looks broken to clients
- A single API timeout fails the entire Brownfield run instead of retrying once
- Progress callbacks fire "started" but never "completed"

**Files to change:**
- `swarms/brownfield.py`
- `swarms/greyfield.py`

**Exact change — BrownfieldSwarm:**

The `_run_stage_with_retry` method already exists on `GreenfieldSwarm`. The fix is:

1. Copy `_run_stage_with_retry` verbatim from `swarms/greenfield.py` into `swarms/base_swarm.py` (on `BaseSwarm`), so all three swarms inherit it. Then remove it from `greenfield.py` (it will inherit from base).

   *OR* (simpler): Copy `_run_stage_with_retry` into both `BrownfieldSwarm` and `GreyfieldSwarm` as a local method. Less clean but zero risk of greenfield regression.

   **Recommended approach: move to BaseSwarm.**

2. In `BrownfieldSwarm.execute()`, replace every pattern of:
   ```python
   self._emit_progress("stage_name", "started")
   result = self._run_stage(...)
   if self._cost_exceeded:
       return self._finalize_run("cost_exceeded")
   ```
   with:
   ```python
   result = self._run_stage_with_retry("stage_name", self._run_stage, ...)
   if self._cost_exceeded:
       return self._finalize_run("cost_exceeded")
   ```

3. Do the same for every stage in `GreyfieldSwarm.execute()`.

4. **Parallel stages in GreyfieldSwarm:** The `_run_parallel_analysis` method runs Discovery + Legacy in a `ThreadPoolExecutor`. This is already inside `execute()`, so wrap the whole parallel block in a single stage timing wrapper:
   ```python
   pain_matrix, legacy_result = self._run_stage_with_retry(
       "discovery_legacy_parallel", self._run_parallel_analysis, input_data
   )
   ```

**Acceptance criteria:**
- Run `python main.py --input demo/brownfield/legacy_system_description.txt --client "Test" --quality standard`
- The cost summary table at the end shows **stage rows** (legacy_analysis, refactoring_plan, estimation, synthesis, proposal) with times and costs
- If you mock a transient failure on the first attempt, the stage retries and succeeds on the second

---

## Task 2: Fix Silent LLM Classification Error

**Why:** In `router/classifier.py`, `InputClassifier.classify()`:

```python
try:
    return self._llm_classify(input_content, input_path)
except Exception as e:
    pass  # ← error silently swallowed
```

When LLM classification fails (API error, bad response), it silently falls back to heuristics. This is the right behaviour, but the exception is completely hidden — you will never know classification is degraded.

**File:** `router/classifier.py`

**Change:** Replace the `pass` with a structured log warning:

```python
except Exception as e:
    import structlog
    structlog.get_logger().warning(
        "llm_classify_failed",
        error=str(e),
        error_type=type(e).__name__,
        fallback="heuristic",
    )
```

**Acceptance:** Running with an invalid API key (or mocking a failure) logs a `WARNING` event `llm_classify_failed` and still returns a classification result.

---

## Task 3: Verify Log File Handle Cleanup

**Why:** The logger opens a file stream; if it's not closed on exit it can leave handles open on long-running or repeatedly-invoked CLI sessions.

**File:** `utils/logging.py`

**Steps:**
1. Read the file.
2. Look for the line that opens the log file stream (e.g. `open(log_path, ...)`).
3. If `atexit.register(...)` already closes that handle, mark **done**.
4. If not, add:
   ```python
   import atexit
   # After: _file_stream = open(log_path, ...)
   atexit.register(_file_stream.close)
   ```

**Acceptance:** No change needed if already present. If added, a full run completes without ResourceWarning.

---

## Task 4: Verify `run_metadata.json` Uses Real Cost (SwarmCostLogger)

**Why:** There have been two cost-tracking systems in this codebase: (1) `SwarmCostLogger` (real LiteLLM API cost) and (2) legacy token-based estimates in agents. The `CostController` was already moved to use the logger, but `run_metadata.json` still writes `token_usage.total_cost_usd`. Verify this value comes from the logger.

**File:** `swarms/base_swarm.py` → `save_artifacts()`

**Steps:**
1. Read `save_artifacts()`. Find where `run_meta["token_usage"]["total_cost_usd"]` is set.
2. Confirm it uses `get_cost_controller().total_cost_usd` (which reads from `SwarmCostLogger`), not `self.run.token_usage.total_cost` (the old agent-level estimate).
3. If it uses the old path, change it:
   ```python
   # In save_artifacts(), run_meta["token_usage"]:
   "total_cost_usd": get_cost_controller().total_cost_usd,   # <- must be this
   ```
4. Also verify `_check_cost_limit()` in `BaseSwarm` uses `get_cost_controller().total_cost_usd` for its comparison (it already does as of last review — just confirm no regression).

**Acceptance:** After a full run, `outputs/<run_id>/run_metadata.json` has `token_usage.total_cost_usd` matching the total shown in the cost summary table.

---

## Task 5: Full End-to-End Smoke Test (All Three Modes)

**Why:** Verify that Tasks 1–4 together produce working pipelines. Run this after completing Tasks 1–4.

**Steps:**

```bash
# 1. Import sanity
python -c "
from main import main
from orchestrator import EngagementManager, run_factory
from swarms import GreenfieldSwarm, GreenfieldInput
from swarms import BrownfieldSwarm, BrownfieldInput
from swarms import GreyfieldSwarm, GreyfieldInput
from orchestrator.cost_controller import get_cost_controller, reset_cost_controller
from utils.logging import setup_logging
print('All imports OK')
"

# 2. List providers
python main.py --list-providers

# 3. Greenfield run
python main.py --input workspace/sample_transcript.txt --client "Smoke-GF" --quality standard

# 4. Brownfield run
python main.py --input demo/brownfield/legacy_system_description.txt --client "Smoke-BF" --mode brownfield

# 5. Greyfield run
python main.py \
  --input demo/greyfield/new_requirements.txt \
  --codebase demo/greyfield/existing_system.txt \
  --client "Smoke-GY" --mode greyfield

# 6. Check all three produced cost tables and proposal.md
for RUN_ID in $(ls -t outputs | grep '^run_' | head -3); do
  echo "--- $RUN_ID ---"
  test -f "outputs/$RUN_ID/proposal.md" && echo "proposal.md OK" || echo "MISSING proposal.md"
  test -f "outputs/$RUN_ID/run_metadata.json" && \
    python -c "
import json; m=json.loads(open('outputs/$RUN_ID/run_metadata.json').read())
cost=m.get('token_usage',{}).get('total_cost_usd','MISSING')
print(f'  cost_usd={cost}')
"
done
```

**Acceptance:**
- All three modes complete with status `completed`
- All produce `proposal.md`
- `run_metadata.json` shows a non-zero `total_cost_usd` for each
- Cost summary table (printed to stdout) shows stage rows for all three modes (this confirms Task 1 is working)

---

# PRIORITY 2 — Dead Code & Consistency

---

## Task 6: Delete Dead Code — `run_critic_loop` Standalone Function

**Why:** `critic_agent.py` contains a standalone `run_critic_loop()` function at the bottom of the file (lines ~261–311). It is **never called** anywhere — `BaseSwarm.run_with_critique()` is the live mechanism. The standalone function duplicates the logic and will confuse future readers.

**File:** `agents/critic_agent.py`

**Change:** Delete the entire `run_critic_loop` function and any imports it uses exclusively (check with grep). Do not touch `CriticAgent` class or the `review()` method.

**Acceptance:**
- `grep -rn "run_critic_loop" .` returns no hits
- `pytest tests/ -v` still passes

---

## Task 7: Delete Legacy Cost Types from `cost_controller.py`

**Why:** `orchestrator/cost_controller.py` contains two types that are explicitly marked "legacy" in their docstrings and are no longer used:
- `AgentCostRecord` (dataclass) — `record_usage()` is a documented no-op
- `TokenUsage` (dataclass) — duplicate of the Pydantic `TokenUsage` in `agents/base_agent.py`

**File:** `orchestrator/cost_controller.py`

**Steps:**
1. Delete the `@dataclass class TokenUsage(...)` definition (the dataclass one — NOT the Pydantic one in `agents/base_agent.py`).
2. Delete the `@dataclass class AgentCostRecord(...)` definition.
3. Delete `record_usage()` method on `CostController` (it's already a documented no-op).
4. Run `grep -rn "AgentCostRecord\|from orchestrator.cost_controller import.*TokenUsage" .` — fix any remaining references.

**Note:** `TokenUsage` in `agents/base_agent.py` (Pydantic `BaseModel`) is the live version — **do not touch it**.

**Acceptance:**
- `python -c "from orchestrator.cost_controller import CostController; c=CostController(); print('OK')"` works
- `pytest tests/ -v` still passes

---

## Task 8: Rename `self.run` → `self._run_record` in BaseSwarm

**Why:** `BaseSwarm.__init__` sets `self.run = SwarmRun(...)`. `run` is a conventional method name in Python and in this codebase (`swarm.execute()` is the public API but `swarm.run` exists on the abstract base). Any developer who calls `swarm.run(input_data)` expecting the execution method gets a `SwarmRun is not callable` error — confusing and hard to debug.

**File:** `swarms/base_swarm.py` (and all subclasses)

**Steps:**
1. In `base_swarm.py`:
   - In `__init__`: change `self.run = SwarmRun(...)` → `self._run_record = SwarmRun(...)`
   - Everywhere `self.run.` appears: replace with `self._run_record.`
2. In `swarms/greenfield.py`, `swarms/brownfield.py`, `swarms/greyfield.py`, `swarms/ingestion_swarm.py`:
   - Replace all `self.run.` → `self._run_record.`
3. Do a final `grep -rn "self\.run\." swarms/` to confirm no references remain.

**Acceptance:** All integration tests pass; `grep -rn "self\.run\." swarms/` returns no hits.

---

## Task 9: Replace `print()` with `structlog` in Budget Warning

**Why:** `providers/cost_logger.py` has a budget-at-80% warning that uses `print()` directly. All other logging in the codebase uses `structlog`. The print goes to stdout mixed in with Rich UI output, which looks messy and doesn't appear in `run.log`.

**File:** `providers/cost_logger.py` — `SwarmCostLogger.log_success_event()`

**Change:** Replace:
```python
print(f"  [BUDGET WARNING] Total ${self.total_cost:.2f} >= 80% of max_budget ${max_budget:.2f}. Remaining: ${remaining:.2f}")
```
with:
```python
import structlog
structlog.get_logger().warning(
    "budget_warning",
    total_cost_usd=round(self.total_cost, 4),
    max_budget_usd=max_budget,
    remaining_usd=round(remaining, 4),
    threshold_pct=80,
)
```

Also check for the `print(f"  [{agent} tier:{tier} {model}] → ${cost:.4f}")` line in the same method. This is live per-call logging. It's fine for development but noisy in production. Change it to a `structlog.get_logger().debug(...)` call so it doesn't appear unless verbose mode is on.

**Acceptance:** A run that approaches 80% of budget logs a `budget_warning` event in `run.log` (check with `grep budget_warning outputs/latest/run.log`); per-call cost lines no longer appear on stdout unless verbose.

---

## Task 10: Clean Up Dual Virtual Environments

**Why:** Both `.venv/` and `venv/` exist. This is confusing (which one is active?) and wastes disk space.

**Steps:**
1. Determine which is active: `which python` — it will show `.venv` or `venv` in the path.
2. If `.venv` is active (README says use `.venv`): delete `venv/` with `rm -rf venv/`.
3. If `venv` is active: either rename (not recommended) or just keep `.venv` and update `.gitignore` to ignore both (`venv/` and `.venv/`).
4. Verify `.gitignore` ignores whichever one you keep.

**After deletion:**
```bash
# Confirm the correct venv still works
source .venv/bin/activate
python -c "import litellm; import pydantic; print('OK')"
```

**Acceptance:** Only one venv directory exists; `source .venv/bin/activate && python main.py --help` works.

---

# PRIORITY 3 — Housekeeping & Docs

---

## Task 11: Seed Historical Data (if not already done)

**Why:** Reference forecasting and the accuracy reporting dashboard need data. If `data/historical_projects.json` is empty or has zero projects, `--use-reference-forecast` does nothing useful.

**Check first:**
```bash
python -c "from utils.historical_db import load_historical_db; db=load_historical_db(); print(f'{len(db.projects)} projects')"
```

If it prints 2 or more, this task is **done — skip it**.

**Steps (if 0 projects):**

1. Run `scripts/seed_historical_data.py` if it exists, or add 2–3 synthetic records manually.

2. If the seed script doesn't exist, create it at `scripts/seed_historical_data.py`:

```python
"""Seed 3 synthetic historical projects into data/historical_projects.json."""
from datetime import date
from contracts.outcomes import ProjectOutcome, PhaseOutcome
from utils.historical_db import add_outcome

SEED_PROJECTS = [
    ProjectOutcome(
        run_id="seed_001",
        client_name="Acme Logistics",
        project_name="Driver manifest app",
        mode="greenfield",
        quality="standard",
        domain="logistics",
        project_type="mobile_app",
        team_size=3,
        phases=[
            PhaseOutcome(
                phase_name="POC",
                estimated_hours=40,
                actual_hours=35,
                accuracy_ratio=0.875,
            ),
            PhaseOutcome(
                phase_name="MVP",
                estimated_hours=120,
                actual_hours=155,
                accuracy_ratio=1.29,
            ),
        ],
        total_estimated_hours=160,
        total_actual_hours=190,
        overall_accuracy_ratio=1.19,
        project_completed_date=date(2025, 2, 1),
        notes="Mobile app for real-time driver manifests. MVP ran long due to GPS integration complexity.",
    ),
    ProjectOutcome(
        run_id="seed_002",
        client_name="Beta Finance",
        project_name="API integration hub",
        mode="greenfield",
        quality="premium",
        domain="fintech",
        project_type="api_integration",
        team_size=4,
        phases=[
            PhaseOutcome(
                phase_name="POC",
                estimated_hours=30,
                actual_hours=28,
                accuracy_ratio=0.93,
            ),
            PhaseOutcome(
                phase_name="MVP",
                estimated_hours=200,
                actual_hours=210,
                accuracy_ratio=1.05,
            ),
        ],
        total_estimated_hours=230,
        total_actual_hours=238,
        overall_accuracy_ratio=1.03,
        project_completed_date=date(2025, 3, 1),
        notes="API hub connecting 5 data providers. On-budget thanks to clear specs.",
    ),
    ProjectOutcome(
        run_id="seed_003",
        client_name="Delta Corp",
        project_name="Legacy monolith refactor",
        mode="brownfield",
        quality="standard",
        domain="enterprise",
        project_type="legacy_modernisation",
        team_size=5,
        phases=[
            PhaseOutcome(
                phase_name="Assessment",
                estimated_hours=40,
                actual_hours=55,
                accuracy_ratio=1.375,
            ),
            PhaseOutcome(
                phase_name="Strangler Fig Phase 1",
                estimated_hours=300,
                actual_hours=420,
                accuracy_ratio=1.4,
            ),
        ],
        total_estimated_hours=340,
        total_actual_hours=475,
        overall_accuracy_ratio=1.40,
        project_completed_date=date(2025, 2, 15),
        notes="Classic brownfield underestimate — legacy debt was worse than documented.",
    ),
]

if __name__ == "__main__":
    for p in SEED_PROJECTS:
        add_outcome(p)
    print(f"Seeded {len(SEED_PROJECTS)} projects.")
```

3. Run it:
```bash
python scripts/seed_historical_data.py
python -c "from utils.historical_db import load_historical_db; db=load_historical_db(); print(f'{len(db.projects)} projects seeded')"
```

**Acceptance:** `load_historical_db()` returns 2+ projects with no `ValidationError`.

---

## Task 12: Move Planning Docs from Root to `docs/`

**Why:** The project root currently contains: `REFINED-ACTION-PLAN.md`, `FORGE-STREAM-PLAN.md`, `PHASES-11-15-IMPLEMENTATION-LOG.md`, `CURSOR-AUTONOMOUS-BUILD.md`. These are build artefacts/history. `docs/` already has PHASE completion docs. Consolidate.

**Steps:**
```bash
git mv REFINED-ACTION-PLAN.md docs/REFINED-ACTION-PLAN.md
git mv FORGE-STREAM-PLAN.md docs/FORGE-STREAM-PLAN.md
git mv PHASES-11-15-IMPLEMENTATION-LOG.md docs/PHASES-11-15-IMPLEMENTATION-LOG.md
git mv CURSOR-AUTONOMOUS-BUILD.md docs/CURSOR-AUTONOMOUS-BUILD.md
```

Update any links in `README.md` that point to these files (e.g. `[FORGE-STREAM-PLAN.md](FORGE-STREAM-PLAN.md)` → `[FORGE-STREAM-PLAN.md](docs/FORGE-STREAM-PLAN.md)`).

**Acceptance:** `ls *.md` at root shows only `README.md` and `completion_plan.md`; all links in README work.

---

## Task 13: Branch Cleanup

**Steps:**
```bash
# Check what exists
git branch -a | grep phases

# Delete local branch (use -D if -d complains about unmerged)
git branch -d phases-11-15-autonomous-build   # adjust name to match

# Delete remote branch if it exists
git push origin --delete phases-11-15-autonomous-build
```

**Acceptance:** `git branch -a | grep phases` returns nothing.

---

## Task 14: Document `--resume` Greenfield-Only Limitation

**Why:** `--resume` is silently broken for Brownfield and Greyfield — `EngagementManager.run_resume` hardcodes `GreenfieldSwarm`. A user who tries `--resume` on a Brownfield run ID gets either a crash or silent incorrect behaviour.

**Two-part fix:**

1. **CLI help text** (`main.py`): Update the `--resume` option's `help` string:
   ```python
   help="Resume a previous GREENFIELD run from the last completed stage. Brownfield/Greyfield not yet supported."
   ```

2. **Runtime guard** (`orchestrator/engagement_manager.py`, `run_resume()`): Add a check at the top of the method:
   ```python
   # Check mode from run_metadata.json
   meta_path = output_path / "run_metadata.json"
   if meta_path.exists():
       meta = json.loads(meta_path.read_text())
       if meta.get("mode") not in ("greenfield", None):
           raise ValueError(
               f"--resume only supports greenfield runs. "
               f"Run {run_id} is mode '{meta.get('mode')}'. "
               "Start a fresh run instead."
           )
   ```

**Acceptance:** `python main.py --resume <brownfield_run_id> --client "X"` prints a clear error message instead of silently running greenfield logic on brownfield artifacts.

---

# Final Verification Checklist

Run this after all tasks are complete:

```bash
# Unit + integration test suite
pytest tests/ -v

# Smoke test (all three modes)
bash scripts/smoke_test.sh   # or run the manual steps from Task 5

# Verify cost data in last run
LATEST=$(ls -t outputs | grep '^run_' | head -1)
python -c "
import json
m = json.loads(open('outputs/$LATEST/run_metadata.json').read())
cost = m.get('token_usage', {}).get('total_cost_usd')
print(f'Cost in metadata: {cost}')
assert cost is not None and cost > 0, 'FAIL: cost missing or zero'
print('PASS')
"

# Historical data
python -c "
from utils.historical_db import load_historical_db
db = load_historical_db()
assert len(db.projects) >= 2, f'FAIL: only {len(db.projects)} projects'
print(f'PASS: {len(db.projects)} projects')
"

# Dead code gone
python -c "
import ast, pathlib
src = pathlib.Path('agents/critic_agent.py').read_text()
assert 'def run_critic_loop' not in src, 'FAIL: dead run_critic_loop still present'
print('PASS: run_critic_loop removed')
"

# No dual venv
python -c "
import pathlib
both = pathlib.Path('venv').exists() and pathlib.Path('.venv').exists()
assert not both, 'FAIL: both venv/ and .venv/ exist'
print('PASS: single venv')
"
```

All assertions must pass. Any failure is a blocker.

---

# File Reference

| Concern | Location |
|---------|----------|
| Stage retry + cost recording | `swarms/base_swarm.py` → move `_run_stage_with_retry` here |
| Brownfield stage calls | `swarms/brownfield.py` → use `_run_stage_with_retry` |
| Greyfield stage calls | `swarms/greyfield.py` → use `_run_stage_with_retry` |
| Silent classify error | `router/classifier.py` → `classify()` except block |
| Log handle cleanup | `utils/logging.py` → atexit |
| Cost in metadata | `swarms/base_swarm.py` → `save_artifacts()` |
| Dead critic function | `agents/critic_agent.py` → `run_critic_loop` (delete) |
| Legacy cost types | `orchestrator/cost_controller.py` → `AgentCostRecord`, `TokenUsage` dataclass (delete) |
| self.run rename | `swarms/base_swarm.py` + all swarm files |
| Budget warning print | `providers/cost_logger.py` → `log_success_event()` |
| Historical data | `scripts/seed_historical_data.py` (create), `data/historical_projects.json` |
| Resume guard | `orchestrator/engagement_manager.py` → `run_resume()` |
| --resume help text | `main.py` → `--resume` option |

---

*End of plan. P1 items are the blocking ones. Execute in order and run the final checklist before handing off to a client.*
