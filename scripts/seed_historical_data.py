#!/usr/bin/env python3
"""Seed the historical project database with 2–3 synthetic outcomes (completion_plan Task 9).

Run from repo root: python scripts/seed_historical_data.py
Creates data/historical_projects.json if missing; adds seed projects for reference forecasting.
"""

import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.outcomes import ProjectOutcome, PhaseOutcome
from utils.historical_db import add_outcome, load_historical_db, DEFAULT_DB_PATH


def _seed_projects() -> None:
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = load_historical_db()
    if len(db.projects) >= 3:
        print(f"Already have {len(db.projects)} projects in historical DB. Skip seeding.")
        return

    seed_outcomes = [
        ProjectOutcome(
            run_id="run_seed_logistics_20250115",
            client_name="Acme Logistics",
            project_name="Driver manifest app",
            mode="greenfield",
            quality="standard",
            domain="logistics",
            project_type="mobile-app",
            team_size=3,
            phases=[
                PhaseOutcome(
                    phase_name="POC",
                    phase_type="poc",
                    estimated_hours=80,
                    actual_hours=92,
                    accuracy_ratio=92 / 80,
                    estimated_weeks=2,
                    actual_weeks=2,
                    estimated_cost_gbp=12000,
                    actual_cost_gbp=13800,
                ),
                PhaseOutcome(
                    phase_name="MVP",
                    phase_type="mvp",
                    estimated_hours=200,
                    actual_hours=210,
                    accuracy_ratio=210 / 200,
                    estimated_weeks=5,
                    actual_weeks=5,
                ),
            ],
            total_estimated_hours=280,
            total_actual_hours=302,
            overall_accuracy_ratio=302 / 280,
            project_completed_date=datetime(2025, 2, 1),
            lessons_learned="POC took longer due to offline sync scope.",
        ),
        ProjectOutcome(
            run_id="run_seed_fintech_20250201",
            client_name="Beta Finance",
            project_name="API integration hub",
            mode="greenfield",
            quality="premium",
            domain="fintech",
            project_type="api-integration",
            team_size=4,
            phases=[
                PhaseOutcome(
                    phase_name="POC",
                    phase_type="poc",
                    estimated_hours=120,
                    actual_hours=115,
                    accuracy_ratio=115 / 120,
                    estimated_weeks=3,
                    actual_weeks=3,
                ),
            ],
            total_estimated_hours=120,
            total_actual_hours=115,
            overall_accuracy_ratio=115 / 120,
            project_completed_date=datetime(2025, 3, 1),
            lessons_learned="Estimate was slightly high; team was experienced.",
        ),
        ProjectOutcome(
            run_id="run_seed_legacy_20250120",
            client_name="Delta Corp",
            project_name="Legacy monolith refactor",
            mode="brownfield",
            quality="standard",
            domain="logistics",
            project_type="api-integration",
            team_size=2,
            phases=[
                PhaseOutcome(
                    phase_name="POC",
                    phase_type="poc",
                    estimated_hours=60,
                    actual_hours=78,
                    accuracy_ratio=78 / 60,
                    estimated_weeks=2,
                    actual_weeks=2,
                ),
            ],
            total_estimated_hours=60,
            total_actual_hours=78,
            overall_accuracy_ratio=78 / 60,
            project_completed_date=datetime(2025, 2, 15),
            lessons_learned="Legacy coupling was worse than expected.",
        ),
    ]

    for outcome in seed_outcomes:
        add_outcome(outcome)
        print(f"Added: {outcome.client_name} / {outcome.project_name} ({outcome.mode}, {outcome.domain})")

    print(f"Seeded {len(seed_outcomes)} projects. DB: {DEFAULT_DB_PATH}")


if __name__ == "__main__":
    _seed_projects()
