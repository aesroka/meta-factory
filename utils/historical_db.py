"""Manage historical project database (Phase 14)."""

import json
from pathlib import Path
from typing import Optional

from contracts.outcomes import HistoricalDatabase, ProjectOutcome

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "historical_projects.json"


def load_historical_db(path: Optional[Path] = None) -> HistoricalDatabase:
    """Load historical database from JSON."""
    path = path or DEFAULT_DB_PATH
    if not path.exists():
        return HistoricalDatabase(projects=[])
    data = json.loads(path.read_text())
    return HistoricalDatabase(**data)


def save_historical_db(db: HistoricalDatabase, path: Optional[Path] = None) -> None:
    """Save historical database to JSON."""
    path = path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(db.model_dump(), indent=2, default=str))


def add_outcome(outcome: ProjectOutcome, path: Optional[Path] = None) -> None:
    """Add a completed project outcome to the database."""
    path = path or DEFAULT_DB_PATH
    db = load_historical_db(path)
    db.add_project(outcome)
    save_historical_db(db, path)
    out_dir = path.parent / "outcomes"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in outcome.client_name + "_" + outcome.project_name)
    date_str = outcome.project_completed_date.strftime("%Y%m%d") if outcome.project_completed_date else "unknown"
    outcome_file = out_dir / f"{safe_name}_{date_str}.json"
    outcome_file.write_text(json.dumps(outcome.model_dump(), indent=2, default=str))
