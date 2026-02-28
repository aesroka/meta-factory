# Refined Action Plan - Post-Cursor Review

**Status:** Phases 11-15 complete, 3 critical fixes needed before merge
**Timeline:** 30 minutes to merge-ready, 6.5 hours to fully polished

---

## Immediate Actions (Before Merge) - 30 minutes

### Fix #1: Add Dependencies to requirements.txt ⚠️ CRITICAL
**Time:** 2 minutes
**Status:** BLOCKING MERGE

```bash
cd /Users/adam.sroka/Documents/CODE/meta-factory
git checkout phases-11-15-autonomous-build

# Verify current state
grep -E "(structlog|pyyaml)" requirements.txt

# If missing (they probably are), add them
cat >> requirements.txt << 'EOF'

# Phase 11 & 13 dependencies
structlog>=23.1.0
pyyaml>=6.0
EOF

# Test install
pip install structlog pyyaml

# Commit
git add requirements.txt
git commit -m "Fix: Add missing dependencies (structlog, pyyaml) from phases 11 & 13"
```

**Verification:**
```bash
# Fresh install test
python3 -m venv /tmp/test_venv
source /tmp/test_venv/bin/activate
pip install -r requirements.txt
python -c "import struct log; import yaml; print('✅ Dependencies OK')"
deactivate
rm -rf /tmp/test_venv
```

---

### Fix #2: Close File Handle in Logging ⚠️ MEDIUM
**Time:** 5 minutes
**Status:** Should fix before merge

**Edit:** `utils/logging.py`

```python
# Line 1: Add import
import atexit

# Line 20-21: Change from:
    log_path = output_dir / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _file_stream = open(log_path, "a", encoding="utf-8")

# To:
    log_path = output_dir / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _file_stream = open(log_path, "a", encoding="utf-8")
    atexit.register(_file_stream.close)  # Ensure cleanup on exit
```

**Commit:**
```bash
git add utils/logging.py
git commit -m "Fix: Close log file handle on exit (prevent handle leak)"
```

---

### Fix #3: End-to-End Smoke Test ✅ VERIFICATION
**Time:** 5 minutes
**Status:** Ensure system works

```bash
# Activate venv
source .venv/bin/activate

# Test 1: List providers
python main.py --list-providers
# Expected: Should show at least OpenAI as ready

# Test 2: Cost estimate
python main.py --estimate-only --input workspace/sample_transcript.txt --client "Smoke-Test"
# Expected: Show cost range $0.80-$3.00, prompt to proceed
# Action: Type 'n' to cancel

# Test 3: Classify only
python main.py --classify-only --input workspace/sample_transcript.txt --client "Smoke-Test"
# Expected: Show classification (GREENFIELD), confidence, evidence

# Test 4: Full run (standard quality)
python main.py --input workspace/sample_transcript.txt --client "Smoke-Test" --quality standard
# Expected: Complete in 3-5 minutes, generate proposal
# Verify: outputs/run_*/proposal.md exists
# Verify: outputs/run_*/run.log exists with JSON

# Test 5: Check logging
LATEST_RUN=$(ls -t outputs/ | grep run_ | head -1)
echo "Latest run: $LATEST_RUN"
head -5 outputs/$LATEST_RUN/run.log
# Expected: See JSON log lines with timestamps

# Test 6: Verify cost table printed
# (Should have seen it in Test 4 output)

echo "✅ All smoke tests passed"
```

**If any test fails:** Document in BLOCKERS.md, fix before merge.

---

### Fix #4: Merge to Main 🚢 SHIP IT
**Time:** 5 minutes
**Status:** After fixes 1-3 complete

```bash
# Ensure all fixes committed
git status
# Should be clean

# Review commits
git log --oneline -10

# Switch to main
git checkout main

# Merge feature branch
git merge phases-11-15-autonomous-build

# Tag release
git tag -a v1.1-internal-tooling -m "Phases 11-15: Internal Consultancy Tooling

Features:
- Production reliability (structured logging, cost tables)
- Proposal iteration (diff engine, variations, baseline comparison)
- Prompt gallery (YAML prompts, A/B testing for Discovery agent)
- Reference forecasting (historical database, accuracy tracking)
- Production polish (cost prediction, friendly errors)

Changes: +1,500 LOC across 14 new files
Tests: 125/125 passing
Grade: A- (91/100)

Ready for daily team use."

# Push
git push origin main --tags

echo "🎉 v1.1 shipped!"
```

---

## Phase 2: Polish Features (Week 1) - 6 hours

### Task #1: Convert Remaining Agents to YAML Prompts
**Priority:** HIGH
**Time:** 3-4 hours
**Why:** Team needs to edit prompts without coding

**Agents to convert:**
1. `architect_agent.py` → `agents/prompts/architect.yaml` (45 min)
2. `estimator_agent.py` → `agents/prompts/estimator.yaml` (45 min)
3. `proposal_agent.py` → `agents/prompts/proposal.yaml` (45 min)
4. `synthesis_agent.py` → `agents/prompts/synthesis.yaml` (30 min)
5. `critic_agent.py` → `agents/prompts/critic.yaml` (30 min)
6. `miner_agent.py` → `agents/prompts/miner.yaml` (30 min)

**Process for each agent:**

```bash
# 1. Extract existing prompt
cat agents/architect_agent.py | grep -A 100 "SYSTEM_PROMPT ="

# 2. Create YAML file
cat > agents/prompts/architect.yaml << 'EOF'
version: "1.0"

system_prompt: |
  [paste SYSTEM_PROMPT here]

variants:
  default:
    system_prompt: |
      [same as above]
  concise:
    system_prompt: |
      [shorter version - reduce by 30%]

examples: []
metadata:
  author: "Adam"
  last_updated: "2026-02-24"
  tags: ["architect", "eip", "atam"]
EOF

# 3. Update agent file
# Remove SYSTEM_PROMPT class attribute
# Add prompt_variant parameter to __init__
# Remove system_prompt=self.SYSTEM_PROMPT from super().__init__

# 4. Test
python -c "
from agents import ArchitectAgent
agent = ArchitectAgent()
print(f'✅ Architect agent loads prompt: {len(agent.system_prompt)} chars')
"

# 5. Commit
git add agents/prompts/architect.yaml agents/architect_agent.py
git commit -m "Convert ArchitectAgent to YAML prompts

- Extract system prompt to agents/prompts/architect.yaml
- Add 'concise' variant (30% shorter)
- Update agent to load from YAML
- Tested: prompt loads correctly"
```

**Acceptance:** All 6 agents load prompts from YAML, team can edit without coding.

---

### Task #2: Add Streaming Progress
**Priority:** MEDIUM
**Time:** 2 hours
**Why:** Premium runs give no feedback (bad UX)

**Step 1: Add progress callback to BaseSwarm** (30 min)

```python
# swarms/base_swarm.py

from typing import Callable, Optional

class BaseSwarm:
    def __init__(
        self,
        librarian=None,
        run_id=None,
        provider=None,
        model=None,
        prompt_variant="default",
        progress_callback: Optional[Callable] = None,  # NEW
    ):
        # ... existing code
        self.progress_callback = progress_callback

    def _emit_progress(self, stage: str, status: str, **kwargs):
        """Emit progress update if callback is registered."""
        if self.progress_callback:
            try:
                self.progress_callback(stage=stage, status=status, **kwargs)
            except Exception:
                pass  # Don't let callback errors break pipeline

    def _run_stage_with_retry(self, stage_name, stage_fn, *args, **kwargs):
        self._emit_progress(stage_name, "started")
        start = time.time()

        try:
            result = stage_fn(*args, **kwargs)
            duration = time.time() - start
            cost = self.cost_controller.get_stage_cost(stage_name)

            self._emit_progress(
                stage_name,
                "completed",
                duration_s=duration,
                cost_usd=cost,
            )
            return result
        except Exception as e:
            duration = time.time() - start
            self._emit_progress(
                stage_name,
                "failed",
                duration_s=duration,
                error=str(e),
            )
            raise
```

**Step 2: Add Live table to main.py** (60 min)

```python
# main.py

from rich.live import Live
from rich.table import Table
import threading

def main(...):
    # ... existing setup code

    # Progress tracking
    progress_data = {}
    progress_lock = threading.Lock()

    def update_progress(stage, status, **kwargs):
        """Callback for swarm progress updates."""
        with progress_lock:
            progress_data[stage] = {"status": status, **kwargs}

    def generate_progress_table():
        """Generate Rich table from progress data."""
        with progress_lock:
            table = Table(title="Meta-Factory Progress", show_lines=True)
            table.add_column("Stage", style="cyan")
            table.add_column("Status", style="bold")
            table.add_column("Duration", justify="right")
            table.add_column("Cost", justify="right", style="green")

            for stage, data in progress_data.items():
                status_icon = {
                    "started": "⏳",
                    "completed": "✅",
                    "failed": "❌",
                }.get(data["status"], "❓")

                status_text = f"{status_icon} {data['status']}"
                duration = f"{data.get('duration_s', 0):.1f}s" if "duration_s" in data else "-"
                cost = f"${data.get('cost_usd', 0):.3f}" if "cost_usd" in data else "-"

                table.add_row(stage, status_text, duration, cost)

            return table

    # Run with live progress
    with Live(generate_progress_table(), refresh_per_second=2, console=console) as live:
        def refresh_display(**kwargs):
            update_progress(**kwargs)
            live.update(generate_progress_table())

        result = run_factory(
            ...,
            progress_callback=refresh_display,
        )
```

**Step 3: Thread progress_callback through** (30 min)

```python
# orchestrator/engagement_manager.py
def run_factory(..., progress_callback=None):
    # Pass to swarm
    swarm = get_swarm(..., progress_callback=progress_callback)
```

**Test:**
```bash
python main.py --input workspace/sample_transcript.txt --client "Progress-Test" --quality premium
# Should show live-updating table:
# Stage          | Status      | Duration | Cost
# Discovery      | ✅ completed| 12.3s    | $0.082
# Architecture   | ⏳ started  | -        | -
```

**Commit:**
```bash
git add swarms/base_swarm.py main.py orchestrator/engagement_manager.py
git commit -m "Add streaming progress with live table

- BaseSwarm emits progress events (started/completed/failed)
- main.py shows Rich Live table with stage-by-stage progress
- Improves UX for long-running premium quality
- Thread-safe progress updates"
```

---

### Task #3: Seed Sample Historical Data
**Priority:** LOW
**Time:** 30 minutes
**Why:** Lets you demo reference forecasting

```bash
# Create sample historical data
mkdir -p data/outcomes

cat > data/historical_projects.json << 'EOF'
{
  "projects": [
    {
      "run_id": "sample_001",
      "client_name": "Acme Logistics",
      "project_name": "Digital Manifest System",
      "mode": "greenfield",
      "quality": "standard",
      "domain": "logistics",
      "project_type": "mobile-app",
      "team_size": 3,
      "phases": [
        {
          "phase_name": "POC – Technical Validation",
          "phase_type": "poc",
          "estimated_hours": 79,
          "actual_hours": 95,
          "accuracy_ratio": 1.20,
          "estimated_cost_gbp": 11800,
          "actual_cost_gbp": 14250,
          "estimated_weeks": 4,
          "actual_weeks": 5,
          "notes": "Underestimated integration with legacy routing service"
        },
        {
          "phase_name": "MVP – Core Digital Manifest",
          "phase_type": "mvp",
          "estimated_hours": 113,
          "actual_hours": 145,
          "accuracy_ratio": 1.28,
          "estimated_cost_gbp": 16902,
          "actual_cost_gbp": 21750,
          "estimated_weeks": 6,
          "actual_weeks": 8,
          "notes": "Conflict resolution UI took longer than expected"
        }
      ],
      "total_estimated_hours": 192,
      "total_actual_hours": 240,
      "overall_accuracy_ratio": 1.25,
      "proposal_generated_date": "2026-01-15T10:00:00",
      "project_completed_date": "2026-03-01T17:00:00",
      "lessons_learned": "Always add 30% buffer for legacy integrations",
      "tags": ["mobile", "offline-first", "legacy-integration"]
    },
    {
      "run_id": "sample_002",
      "client_name": "TechCo",
      "project_name": "API Integration Platform",
      "mode": "greenfield",
      "quality": "standard",
      "domain": "fintech",
      "project_type": "api-integration",
      "team_size": 2,
      "phases": [
        {
          "phase_name": "POC",
          "phase_type": "poc",
          "estimated_hours": 60,
          "actual_hours": 72,
          "accuracy_ratio": 1.20,
          "estimated_weeks": 3,
          "actual_weeks": 4,
          "notes": "OAuth flow more complex than anticipated"
        }
      ],
      "total_estimated_hours": 60,
      "total_actual_hours": 72,
      "overall_accuracy_ratio": 1.20,
      "proposal_generated_date": "2026-02-01T10:00:00",
      "project_completed_date": "2026-02-28T17:00:00",
      "lessons_learned": "Always prototype auth flows first",
      "tags": ["api", "oauth", "fintech"]
    }
  ]
}
EOF

# Test forecast report
python scripts/forecast_report.py
# Expected output:
# Historical Database
# Total projects: 2
#
# Accuracy by Mode
# Mode       | Projects | Avg Accuracy | Correction Factor
# greenfield | 2        | 1.23x        | 1.23x
#
# Recent Projects
# • Acme Logistics - Digital Manifest System (greenfield)
#   Estimated: 192h, Actual: 240h (1.25x)
# • TechCo - API Integration Platform (greenfield)
#   Estimated: 60h, Actual: 72h (1.20x)

# Test reference-adjusted estimation
python main.py --input workspace/sample_transcript.txt --client "Ref-Test" --use-reference-forecast
# Should apply 1.23x correction to all estimates
# Check outputs/run_*/estimation.json for adjusted numbers

# Commit
git add data/historical_projects.json
git commit -m "Seed sample historical data for demo

- 2 completed greenfield projects
- Average 1.23x accuracy ratio
- Enables reference forecasting demo
- Scripts/forecast_report.py now shows data"
```

---

## Phase 3: Optional Optimizations (Next 2 Weeks) - 4 hours

### Task #4: Parallel Ensemble Estimation
**Priority:** LOW (only if team uses premium regularly)
**Time:** 1 hour

```python
# swarms/greenfield.py
from concurrent.futures import ThreadPoolExecutor
import time

def _run_estimation(self, architecture, ensemble=True):
    if not ensemble:
        return self._run_single_estimate(EstimatorAgent, architecture)

    # Parallel ensemble
    from agents.estimation_ensemble import (
        OptimistEstimator,
        PessimistEstimator,
        RealistEstimator,
    )
    from agents.estimation_aggregator import aggregate_ensemble

    logger.info("ensemble_estimation_started", mode="parallel")

    def run_estimator(agent_class, name):
        """Run estimator in thread."""
        start = time.time()
        agent = agent_class(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        result = agent.run(EstimatorInput(architecture=architecture))
        duration = time.time() - start

        logger.info(
            "ensemble_agent_completed",
            agent=name,
            hours=result.output.total_expected_hours,
            cost=result.token_usage.total_cost,
            duration_s=duration,
        )
        return result.output

    # Run all three in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            "optimist": executor.submit(run_estimator, OptimistEstimator, "optimist"),
            "pessimist": executor.submit(run_estimator, PessimistEstimator, "pessimist"),
            "realist": executor.submit(run_estimator, RealistEstimator, "realist"),
        }

        results = {name: future.result() for name, future in futures.items()}

    # Save individual estimates
    self.run.artifacts["estimate_optimist"] = results["optimist"]
    self.run.artifacts["estimate_pessimist"] = results["pessimist"]
    self.run.artifacts["estimate_realist"] = results["realist"]

    # Aggregate
    return aggregate_ensemble(
        results["optimist"],
        results["pessimist"],
        results["realist"],
    )
```

**Test:**
```bash
# Measure sequential (current)
time python main.py --input workspace/sample_transcript.txt --client "Sequential" --quality premium
# Note duration (e.g., 180s)

# Apply parallel patch

# Measure parallel (new)
time python main.py --input workspace/sample_transcript.txt --client "Parallel" --quality premium
# Should be ~60s (3x faster)
```

**Expected speedup:** 3x for premium quality estimation phase

---

### Task #5: Add Caching (Optional)
**Priority:** LOW
**Time:** 1-2 hours

Only do this if you're frequently re-running the same transcript (testing, demos).

---

## Phase 4: Integration & Automation (Ongoing)

### Task #6: Pre-commit Hook
**Time:** 15 minutes

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Ensure tests pass before commit

echo "Running tests..."
pytest -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Fix before committing."
    exit 1
fi

echo "✅ Tests passed"
```

---

### Task #7: GitHub Actions CI (if using GitHub)
**Time:** 30 minutes

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest -v
```

---

## Success Metrics

**After immediate fixes (Phase 1):**
- [ ] Fresh install works (follow README from scratch)
- [ ] All tests pass (125/125)
- [ ] End-to-end smoke test passes
- [ ] Branch merged to main
- [ ] Tagged as v1.1-internal-tooling

**After polish features (Phase 2):**
- [ ] All 7 agents load prompts from YAML
- [ ] Team member can edit prompt and see results
- [ ] Long runs show live progress table
- [ ] Historical database has 2+ projects
- [ ] Reference forecasting applies corrections

**After optimizations (Phase 3):**
- [ ] Premium quality completes in <8 minutes (vs ~25 min)
- [ ] Cached runs return in <2 seconds
- [ ] Parallel ensemble shows 3x speedup

---

## Timeline Summary

| Phase | Duration | When | Critical? |
|-------|----------|------|-----------|
| **Immediate fixes** | 30 min | Today | YES ⚠️ |
| **Polish features** | 6 hours | This week | HIGH |
| **Optimizations** | 4 hours | Next 2 weeks | MEDIUM |
| **CI/CD setup** | 1 hour | Ongoing | LOW |
| **Total** | ~11.5 hours | | |

---

## Final Checklist

**Before merging (30 minutes):**
- [ ] Fix #1: Dependencies in requirements.txt
- [ ] Fix #2: Close file handle in logging
- [ ] Fix #3: End-to-end smoke test passes
- [ ] Fix #4: Merge and tag v1.1

**This week (6 hours):**
- [ ] Task #1: Convert 6 agents to YAML
- [ ] Task #2: Add streaming progress
- [ ] Task #3: Seed historical data

**Nice to have (4 hours):**
- [ ] Task #4: Parallel ensemble
- [ ] Task #5: Caching

---

## Questions?

**Q: Can I skip the polish features?**
A: Yes, but you'll be missing major value. YAML prompts (#1) and streaming progress (#2) are high-impact. Historical data (#3) is optional.

**Q: What if tests fail after fixes?**
A: Document in BLOCKERS.md, don't merge until resolved.

**Q: Can I do parallel ensemble first?**
A: Yes, it's independent. But YAML prompts are higher priority for team usability.

**Q: Should I implement caching?**
A: Only if you're frequently testing with same inputs. Low ROI otherwise.

---

**Ready to go!** Start with the 30-minute immediate fixes, then tackle polish features at your pace.
