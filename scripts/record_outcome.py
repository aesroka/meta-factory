#!/usr/bin/env python3
"""Record actual project outcome for reference class forecasting (Phase 14).

Usage:
  python scripts/record_outcome.py --run-id run_20260213_145954 --domain logistics --project-type mobile-app --team-size 3
"""

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts.outcomes import ProjectOutcome, PhaseOutcome
from utils.historical_db import add_outcome


def main() -> None:
    try:
        import click
    except ImportError:
        print("Install click: pip install click")
        sys.exit(1)

    @click.command()
    @click.option("--run-id", required=True, help="Original proposal run_id")
    @click.option("--domain", required=True, help="Project domain (e.g. logistics, fintech)")
    @click.option("--project-type", required=True, help="Project type (e.g. mobile-app, api-integration)")
    @click.option("--team-size", type=int, required=True, help="Number of developers")
    @click.option("--completed-date", default=None, help="Completion date YYYY-MM-DD (default: today)")
    @click.option("--lessons-learned", default="", help="Optional lessons learned")
    def run(run_id: str, domain: str, project_type: str, team_size: int, completed_date: str, lessons_learned: str) -> None:
        run_path = REPO_ROOT / "outputs" / run_id
        if not run_path.is_dir():
            print(f"Run not found: {run_path}")
            sys.exit(1)
        proposal_path = run_path / "proposal.json"
        if not proposal_path.exists():
            print(f"proposal.json not found in {run_path}")
            sys.exit(1)
        proposal = json.loads(proposal_path.read_text())
        metadata = {}
        meta_path = run_path / "run_metadata.json"
        if meta_path.exists():
            metadata = json.loads(meta_path.read_text())

        phases_in = proposal.get("delivery_phases", [])
        if not phases_in:
            print("No delivery_phases in proposal. Add outcome manually or use a proposal with phases.")
            sys.exit(1)

        phase_outcomes = []
        total_est = 0.0
        total_act = 0.0
        for ph in phases_in:
            est_h = ph.get("estimated_hours", 0)
            act_h = click.prompt(f"  Actual hours for {ph.get('phase_name', '?')}", type=float, default=est_h)
            est_w = ph.get("estimated_weeks", 1)
            act_w = click.prompt(f"  Actual weeks for {ph.get('phase_name', '?')}", type=int, default=est_w)
            ratio = act_h / est_h if est_h else 1.0
            phase_outcomes.append(
                PhaseOutcome(
                    phase_name=ph.get("phase_name", "?"),
                    phase_type=ph.get("phase_type", "poc"),
                    estimated_hours=est_h,
                    actual_hours=act_h,
                    accuracy_ratio=ratio,
                    estimated_weeks=est_w,
                    actual_weeks=act_w,
                )
            )
            total_est += est_h
            total_act += act_h
        overall_ratio = total_act / total_est if total_est else 1.0
        completed_dt = datetime.strptime(completed_date, "%Y-%m-%d") if completed_date else datetime.now()

        outcome = ProjectOutcome(
            run_id=run_id,
            client_name=proposal.get("client_name", "?"),
            project_name=proposal.get("title", "?"),
            mode=metadata.get("mode", "greenfield"),
            quality=metadata.get("quality", "standard"),
            domain=domain,
            project_type=project_type,
            team_size=team_size,
            phases=phase_outcomes,
            total_estimated_hours=total_est,
            total_actual_hours=total_act,
            overall_accuracy_ratio=overall_ratio,
            project_completed_date=completed_dt,
            lessons_learned=lessons_learned,
        )
        add_outcome(outcome)
        print(f"Recorded outcome for {run_id}. Correction factor: {overall_ratio:.2f}x")

    run()


if __name__ == "__main__":
    main()
