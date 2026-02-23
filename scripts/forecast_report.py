#!/usr/bin/env python3
"""Show reference class forecasting accuracy report (Phase 14)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.historical_db import load_historical_db, DEFAULT_DB_PATH


def main() -> None:
    db = load_historical_db()
    if not db.projects:
        print("No historical projects in database.")
        print(f"Add outcomes with: python scripts/record_outcome.py --run-id RUN_ID --domain DOMAIN --project-type TYPE --team-size N")
        print(f"Database path: {DEFAULT_DB_PATH}")
        return
    print(f"Reference Class Forecasting Report")
    print(f"Total projects: {len(db.projects)}")
    print()
    by_mode = {}
    for p in db.projects:
        by_mode.setdefault(p.mode, []).append(p)
    for mode, projects in by_mode.items():
        median_ratio = sum(p.overall_accuracy_ratio for p in projects) / len(projects)
        print(f"  {mode}: {len(projects)} projects, median accuracy ratio: {median_ratio:.2f}x")
    print()
    print("Recent projects:")
    for p in db.projects[-5:]:
        print(f"  - {p.run_id} | {p.client_name} | {p.overall_accuracy_ratio:.2f}x")


if __name__ == "__main__":
    main()
