# Meta-Factory Completion Plan

**Date:** 2026-02-28  
**Author:** Project review (for Cursor coding agent swarm)  
**Target:** Trustworthy, team-usable v1.0  
**Working directory:** `/Users/adam.sroka/Documents/CODE/meta-factory`  
**Branch policy:** All work on `main`. Commit after each task; use conventional commit messages.

**Rough effort:** ~8–12 hours of human-reviewed engineering.

---

## TL;DR

This plan closes the gap between “phases done” and **verified, production-ready** behaviour. There are **12 tasks** in **3 priority tiers**. Do them in order; later tasks assume earlier ones pass.

**Do not skip verification (Tasks 1–4).** Phases 11–15 were generated autonomously and may not have been validated with a real end-to-end run.

| Priority | Focus | Tasks |
|----------|--------|--------|
| **P1** | Verification & critical fixes | 1–4 |
| **P2** | Cost single-source, integration tests, progress UX | 5–8 |
| **P3** | Historical seed data, branch cleanup, docs | 9–12 |

---

## Environment Setup (run once before starting)

```bash
cd /Users/adam.sroka/Documents/CODE/meta-factory
python3 -m venv .venv  # if needed
source .venv/bin/activate   # or: source venv/bin/activate
pip install -r requirements.txt
# Verify at least one provider key is set
python -c "from config import settings; import os; k=os.getenv('OPENAI_API_KEY') or getattr(settings,'openai_api_key',None); print('OpenAI key:', bool(k))"
```

---

# PRIORITY 1 — Verification & Critical Fixes

Must complete before any client use or further feature work.

---

## Task 1: Full End-to-End Smoke Test

**Why:** Phases 11–15 were built autonomously. A full pipeline run may never have been executed. This is the main verification step.

**Deliverable:** No code changes. Run the steps below and record results. If anything fails, fix before proceeding; document failures in `BLOCKERS.md` at repo root.

**Steps:**

1. **Import sanity**
   ```bash
   cd /Users/adam.sroka/Documents/CODE/meta-factory
   source .venv/bin/activate  # or venv/bin/activate
   python -c "
   from main import main
   from orchestrator import EngagementManager, run_factory
   from swarms import GreenfieldSwarm, GreenfieldInput
   from utils.logging import setup_logging
   from orchestrator.cost_controller import get_cost_controller, reset_cost_controller
   print('OK: All imports succeed')
   "
   ```

2. **List providers**
   ```bash
   python main.py --list-providers
   ```
   **Expected:** At least one provider shows "Ready" (e.g. OpenAI). No traceback.

3. **Cost estimate only**
   ```bash
   python main.py --estimate-only --input workspace/sample_transcript.txt --client "Smoke-Test"
   ```
   **Expected:** Cost range (e.g. $0.80–$3.00) and "Proceed with run?" — answer `n` to cancel.

4. **Classify only**
   ```bash
   python main.py --classify-only --input workspace/sample_transcript.txt --client "Smoke-Test"
   ```
   **Expected:** Classification (e.g. GREENFIELD), confidence, evidence, recommended mode.

5. **Full run (standard quality)**
   ```bash
   python main.py --input workspace/sample_transcript.txt --client "Smoke-Test" --quality standard
   ```
   **Expected:** Run completes in a few minutes; cost summary table printed; no unhandled exception.

6. **Artifacts and logs**
   ```bash
   LATEST=$(ls -t outputs | grep '^run_' | head -1)
   test -f "outputs/$LATEST/proposal.md" && echo "proposal.md OK" || echo "MISSING proposal.md"
   test -f "outputs/$LATEST/run.log"     && echo "run.log OK"     || echo "MISSING run.log"
   test -f "outputs/$LATEST/run_metadata.json" && echo "run_metadata.json OK" || echo "MISSING run_metadata.json"
   head -5 "outputs/$LATEST/run.log"
   ```
   **Expected:** All three files exist; `run.log` contains JSON lines with timestamps.

7. **Cost in metadata**
   ```bash
   python -c "
   import json
   from pathlib import Path
   out = Path('outputs')
   runs = sorted([d for d in out.iterdir() if d.is_dir() and (d/'run_metadata.json').exists()], key=lambda d: (d/'run_metadata.json').stat().st_mtime, reverse=True)
   if runs:
       m = json.loads((runs[0]/'run_metadata.json').read_text())
       print('total_cost_usd' in m.get('token_usage', {}), m.get('token_usage', {}))
   "
   ```
   **Expected:** `run_metadata.json` has `token_usage.total_cost_usd` (or equivalent) with a numeric value.

**Acceptance:** All steps pass. If not, create `BLOCKERS.md` with the failing step and error, then fix and re-run until Task 1 passes.

---

## Task 2: Fix Log File Handle Cleanup (if not already done)

**Why:** Avoid file handle leaks on long or repeated runs.

**File:** `utils/logging.py`

**Check:** Ensure the log file handle is closed on process exit.

- If the file already contains `atexit.register(_file_stream.close)` (or equivalent) after opening `_file_stream`, mark this task **done** and skip.
- Otherwise, add:
  - At top: `import atexit`
  - After the line that opens `_file_stream` (e.g. `_file_stream = open(log_path, "a", encoding="utf-8")`), add: `atexit.register(_file_stream.close)`

**Acceptance:** No new handles left open after process exit (manual or tool check); no regression in logging.

---

## Task 3: Resolve Dual Cost System (Single Source: SwarmCostLogger)

**Why:** Cost is currently tracked in two places: (1) LiteLLM `SwarmCostLogger` (real API cost), (2) `TokenUsage.total_cost` in agents (legacy token-based estimate). Budget checks and metadata can disagree. Everything should use the LiteLLM logger as the single source of truth.

**Relevant files:**

- `swarms/base_swarm.py` — `_check_cost_limit()`, `save_artifacts()` (run_metadata)
- `agents/base_agent.py` — `TokenUsage.total_cost` (leave for backward compatibility but stop using for limits)
- `orchestrator/cost_controller.py` — already uses `_logger().total_cost`; no change needed

**Steps:**

1. **Cost limit check**
   - In `swarms/base_swarm.py`, in `_check_cost_limit()`:
     - Replace use of `self.run.token_usage.total_cost` with the cost from the cost controller.
     - Add: `from orchestrator.cost_controller import get_cost_controller` (or keep existing import).
     - Set `current_cost = get_cost_controller().total_cost_usd`.
     - Keep the rest of the logic (compare to `settings.max_cost_per_run_usd`, set `self._cost_exceeded`).
   - Ensure the cost controller is reset at the start of each run (this is already done in `main.py` via `reset_cost_controller()` before the pipeline runs).

2. **Run metadata**
   - In `swarms/base_swarm.py`, in `save_artifacts()`, where `run_metadata` is built:
     - For `token_usage.total_cost_usd`, use `get_cost_controller().total_cost_usd` instead of `self.run.token_usage.total_cost`.
     - Keep `input_tokens` and `output_tokens` from `self.run.token_usage` if they are still populated (for reference). If they are not used elsewhere for decisions, leaving them as-is is fine.

3. **Greenfield / other swarms**
   - In `swarms/greenfield.py` (and any other swarm that writes `run_metadata` or checks cost), ensure cost is read from `get_cost_controller().total_cost_usd` and not from `self.run.token_usage.total_cost`. Align with the pattern in base_swarm.

4. **Docstring**
   - In `orchestrator/cost_controller.py`, the docstring already states that real cost comes from SwarmCostLogger. In `agents/base_agent.py`, add a one-line comment above `TokenUsage.total_cost`: "Legacy; budget and reporting use SwarmCostLogger via CostController."

**Acceptance:**

- Run a full pipeline; when the run finishes, `outputs/<run_id>/run_metadata.json` has `token_usage.total_cost_usd` equal to the sum of costs from the cost summary table (or from SwarmCostLogger).
- A run that exceeds the budget stops and reports cost limit exceeded; the reported total matches the logger.

---

## Task 4: E2E Smoke Test in CI or Script (Optional but Recommended)

**Why:** Lock in Task 1 so regressions are caught.

**Deliverable:** Either a small script or a CI job that runs the same checks as Task 1 (imports, list-providers, estimate-only, classify-only, then optionally one short full run with a tiny input). If you add a script, e.g. `scripts/smoke_test.sh` or `scripts/smoke_test.py`, document it in the README and in this plan.

**Acceptance:** Script (or CI) runs without manual steps and passes when the codebase is healthy.

---

# PRIORITY 2 — Cost Single-Source, Integration Tests, Progress

---

## Task 5: Integration Test — Greenfield

**Why:** No integration tests exist; one per swarm mode gives confidence that the pipeline runs end-to-end with mocks.

**Deliverable:** One integration test that runs the **greenfield** swarm from input to proposal with **mocked** LLM (and RAG if used).

**Location:** `tests/integration/test_greenfield_e2e.py` (create `tests/integration/` if missing).

**Requirements:**

- Mark with `@pytest.mark.integration` so it can be excluded with `pytest -m "not integration"` for fast local runs.
- Mock `litellm.completion` (and any RAG client used by the swarm) so no real API or RAGFlow is called.
- Build a minimal `GreenfieldInput` (e.g. short transcript, client name).
- Run `GreenfieldSwarm(...).execute(input_data)`.
- Assert: return value indicates success; artifacts include expected keys (e.g. `discovery`, `architecture`, `estimation`, `synthesis`, `proposal`); proposal artifact has required structure (e.g. title, delivery_phases or equivalent).

**Acceptance:** `pytest tests/integration/test_greenfield_e2e.py -v` passes with mocks; `pytest -m "not integration"` still runs the rest of the suite without this test if desired.

---

## Task 6: Integration Test — Brownfield

**Why:** Same as Task 5 for brownfield mode.

**Deliverable:** `tests/integration/test_brownfield_e2e.py`.

- Use `BrownfieldInput` with mocked codebase/description (and RAG/LLM as needed).
- Mock LLM and any external services.
- Run `BrownfieldSwarm(...).execute(input_data)`.
- Assert success and presence of key artifacts (e.g. legacy analysis, architecture, proposal).

**Acceptance:** `pytest tests/integration/test_brownfield_e2e.py -v` passes.

---

## Task 7: Integration Test — Greyfield

**Why:** Same as Task 5 for greyfield mode.

**Deliverable:** `tests/integration/test_greyfield_e2e.py`.

- Use `GreyfieldInput` with both transcript and codebase content (mocked).
- Mock LLM and any external services.
- Run `GreyfieldSwarm(...).execute(input_data)`.
- Assert success and key artifacts.

**Acceptance:** `pytest tests/integration/test_greyfield_e2e.py -v` passes.

---

## Task 8: Progress Streaming (BaseSwarm Callback)

**Why:** Long runs (especially premium) give no feedback; a progress callback improves UX.

**Deliverable:**

1. **BaseSwarm**
   - In `swarms/base_swarm.py`:
     - Add optional `progress_callback: Optional[Callable[..., None]] = None` to `__init__` (signature: e.g. `(stage: str, status: str, **kwargs) -> None`). Store as `self.progress_callback`.
     - Add `_emit_progress(self, stage: str, status: str, **kwargs)` that calls `self.progress_callback(stage=stage, status=status, **kwargs)` if set; catch and ignore exceptions so a bad callback does not break the pipeline.
   - Document in the class docstring that callers can pass `progress_callback` to receive stage updates.

2. **GreenfieldSwarm**
   - In `swarms/greenfield.py`, in `execute()` (and any helper that runs stages), call `self._emit_progress(stage_name, "started")` at the start of each stage and `self._emit_progress(stage_name, "completed", duration_s=..., cost_usd=...)` (or `"failed"`, `error=...`) at the end. Use the same stage names as used in logging (e.g. discovery, architecture, estimation, synthesis, proposal).

3. **BrownfieldSwarm / GreyfieldSwarm**
   - Same pattern: at entry/exit of each major stage, call `_emit_progress` with `started` / `completed` or `failed`.

4. **main.py**
   - When building the swarm (e.g. via `EngagementManager` or `run_factory`), pass a progress callback that updates the UI (e.g. Rich Progress or Live). Example: single spinner with current stage name, or a Live table of stages and status. Prefer minimal change: e.g. callback that sets a shared “current stage” string and a Progress spinner in main that reads it.

**Acceptance:** Running `main.py` for a full pipeline shows changing stage names or progress during the run (no long blank period). No regression when `progress_callback` is not passed.

---

# PRIORITY 3 — Data, Cleanup, Docs

---

## Task 9: Seed Historical Data (2–3 Projects)

**Why:** Reference forecasting and accuracy reporting need data; the table says "Seed 2–3 projects."

**Relevant files:**

- `utils/historical_db.py` — `DEFAULT_DB_PATH` = `data/historical_projects.json`
- `contracts/outcomes.py` — `ProjectOutcome`, `PhaseOutcome`, `HistoricalDatabase`
- `scripts/record_outcome.py` — records one outcome from an existing run

**Deliverable:**

1. **Ensure data directory and schema**
   - Create `data/` if it does not exist.
   - If `data/historical_projects.json` does not exist, create it with `{"projects": []}`.

2. **Add 2–3 seed projects**
   - Add 2–3 valid `ProjectOutcome` records. They can be synthetic but must conform to `contracts/outcomes.py` (e.g. `run_id`, `client_name`, `project_name`, `mode`, `quality`, `domain`, `project_type`, `team_size`, `phases` list of `PhaseOutcome`, `total_estimated_hours`, `total_actual_hours`, `overall_accuracy_ratio`, dates, etc.).
   - Option A: Create a script `scripts/seed_historical_data.py` that calls `add_outcome()` (from `utils.historical_db`) for each seed project so the file is written in the same format as production.
   - Option B: Manually write `data/historical_projects.json` with 2–3 entries that validate against `HistoricalDatabase(projects=[...])`.

3. **Document**
   - In README or `docs/USAGE.md`, add a short section "Historical data / Reference forecasting" that explains: where the file lives, how to add outcomes (e.g. `scripts/record_outcome.py` after a real run, or by editing the JSON / running the seed script), and that reference forecasting uses this data when `--use-reference-forecast` is used.

**Acceptance:**

- `python -c "from utils.historical_db import load_historical_db; db=load_historical_db(); print(len(db.projects))"` prints 2 or 3 (or more if you add more).
- No validation error when loading `HistoricalDatabase` from the created file.

---

## Task 10: Branch Cleanup (Stale Remote)

**Why:** Table says "Delete phases-11-15 branch."

**Steps:**

1. List branches: `git branch -a`. If `phases-11-15-autonomous-build` (or similar) exists only locally and has been merged to `main`, delete the local branch: `git branch -d phases-11-15-autonomous-build` (or `-D` if needed).
2. If the branch exists on the remote (e.g. `origin/phases-11-15-autonomous-build`), delete it: `git push origin --delete phases-11-15-autonomous-build` (adjust branch name to match).
3. Do not delete `main` or the current branch.

**Acceptance:** `phases-11-15-autonomous-build` no longer appears in `git branch -a`.

---

## Task 11: Hybrid Context & Reference Forecasting (Document Only)

**Why:** Table marks "Hybrid context" and "Reference forecasting" as built; we only document status and usage.

**Deliverable:**

- In README or `docs/USAGE.md`:
  - **Hybrid context:** One short paragraph: hybrid context (RAG + full context) is implemented; use `--quality premium` or the relevant flag to enable it; it is deprioritised for tuning until proven needed.
  - **Reference forecasting:** One short paragraph: reference forecasting uses `data/historical_projects.json`; seed data (Task 9) should be in place for meaningful corrections; enable with `--use-reference-forecast`.

**Acceptance:** A new team member can find how to enable hybrid context and reference forecasting and where historical data lives.

---

## Task 12: Completion Plan Summary in README

**Why:** So the team knows what “v1.0 completion” meant and where to look for details.

**Deliverable:**

- In `README.md`, add a section **"v1.0 completion"** (or **"Completion checklist"**) that:
  - States that `completion_plan.md` in the repo root describes the full checklist used to reach a team-usable v1.0.
  - Lists the 12 tasks (by number and title) and notes that P1 (verification + cost fix) must pass before client use.
  - Points to this file: `completion_plan.md`.

**Acceptance:** README contains the new section and a correct reference to `completion_plan.md`.

---

# Verification Checklist (Final Pass)

Before considering v1.0 complete, run:

- [ ] Task 1 smoke test (all steps).
- [ ] Task 3: Cost from SwarmCostLogger only; run_metadata and budget check use it.
- [ ] Tasks 5–7: All three integration tests pass.
- [ ] Task 8: Progress callback used in main; stage updates visible during run.
- [ ] Task 9: `load_historical_db()` returns 2+ projects.
- [ ] Task 10: Stale branch removed.
- [ ] `pytest -m "not integration"` passes (or full `pytest` if integration tests are enabled).

---

# File Reference (Quick)

| Concern | Location |
|--------|----------|
| Cost logger (single source) | `providers/cost_logger.py` — `get_swarm_cost_logger()` |
| Cost controller | `orchestrator/cost_controller.py` — `get_cost_controller()`, `total_cost_usd` |
| Budget check in swarm | `swarms/base_swarm.py` — `_check_cost_limit()` |
| Run metadata | `swarms/base_swarm.py` — `save_artifacts()` |
| Historical DB | `utils/historical_db.py`, `data/historical_projects.json` |
| Outcome contract | `contracts/outcomes.py` — `ProjectOutcome`, `PhaseOutcome` |
| Record outcome script | `scripts/record_outcome.py` |
| Integration tests | `tests/integration/` (create if missing) |
| Progress callback | `swarms/base_swarm.py` — add `progress_callback`, `_emit_progress` |

---

*End of completion plan. Execute in order; re-run verification after any change that touches cost or pipeline flow.*
