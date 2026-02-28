#!/usr/bin/env bash
# Smoke test for Meta-Factory (completion_plan Task 4).
# Run from repo root: bash scripts/smoke_test.sh
# Skips full pipeline run unless SMOKE_FULL=1 (to avoid API cost).

set -e
cd "$(dirname "$0")/.."
VENV="${VENV:-.venv}"
if [ -d "$VENV" ]; then
  source "$VENV/bin/activate"
elif [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "=== 1. Import sanity ==="
python -c "
from main import main
from orchestrator import EngagementManager, run_factory
from swarms import GreenfieldSwarm, GreenfieldInput
from utils.logging import setup_logging
from orchestrator.cost_controller import get_cost_controller, reset_cost_controller
print('OK: All imports succeed')
"

echo ""
echo "=== 2. List providers ==="
python main.py --list-providers

echo ""
echo "=== 3. Estimate only (no run) ==="
echo "n" | python main.py --estimate-only --input workspace/sample_transcript.txt --client "Smoke-Test" || true

echo ""
echo "=== 4. Classify only ==="
python main.py --classify-only --input workspace/sample_transcript.txt --client "Smoke-Test"

if [ "${SMOKE_FULL:-0}" = "1" ]; then
  echo ""
  echo "=== 5. Full run (standard) ==="
  python main.py --input workspace/sample_transcript.txt --client "Smoke-Test" --quality standard
  echo ""
  echo "=== 6. Artifacts and logs ==="
  LATEST=$(ls -t outputs 2>/dev/null | grep '^run_' | head -1)
  if [ -n "$LATEST" ]; then
    test -f "outputs/$LATEST/proposal.md" && echo "proposal.md OK" || echo "MISSING proposal.md"
    test -f "outputs/$LATEST/run.log" && echo "run.log OK" || echo "MISSING run.log"
    test -f "outputs/$LATEST/run_metadata.json" && echo "run_metadata.json OK" || echo "MISSING run_metadata.json"
    head -3 "outputs/$LATEST/run.log"
  fi
fi

echo ""
echo "Smoke test completed. Set SMOKE_FULL=1 to include full pipeline run."
