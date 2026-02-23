#!/usr/bin/env python3
"""Compare all variations of a baseline run.

Usage:
  python scripts/compare_variations.py RUN_ID
  python scripts/compare_variations.py run_20260213_145954
"""

import json
import sys
from pathlib import Path

# Add repo root for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from contracts import ProposalDocument


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/compare_variations.py BASELINE_RUN_ID")
        print("Example: python scripts/compare_variations.py run_20260213_145954")
        sys.exit(1)
    baseline_run_id = sys.argv[1]
    outputs = REPO_ROOT / "outputs"
    baseline_path = outputs / baseline_run_id
    if not baseline_path.is_dir():
        print(f"Baseline run not found: {baseline_path}")
        sys.exit(1)

    variations = []
    for run_dir in outputs.iterdir():
        if not run_dir.is_dir():
            continue
        metadata_path = run_dir / "run_metadata.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = json.loads(metadata_path.read_text())
            if metadata.get("baseline") == baseline_run_id:
                variations.append((metadata.get("variation"), run_dir))
        except (json.JSONDecodeError, OSError):
            continue

    if not variations:
        print(f"No variations found for baseline {baseline_run_id}")
        print("Run with: python main.py ... --baseline {} --variation NAME".format(baseline_run_id))
        sys.exit(0)

    try:
        from rich.table import Table
        from rich.console import Console
    except ImportError:
        print("Variations (install 'rich' for table):")
        for var_name, var_path in sorted(variations, key=lambda x: (x[0] or "unnamed")):
            prop_path = var_path / "proposal.json"
            if prop_path.exists():
                doc = ProposalDocument.model_validate_json(prop_path.read_text())
                total_h = doc.total_estimated_hours or sum(p.estimated_hours for p in doc.delivery_phases)
                total_c = sum(p.estimated_cost_gbp or 0 for p in doc.delivery_phases)
                weeks = doc.total_estimated_weeks or doc.timeline_weeks
                print(f"  {var_name or 'unnamed':12} {total_h:.0f}h  £{total_c:,.0f}  {weeks}w  {var_path.name}")
        return

    console = Console()
    table = Table(title=f"Variations of {baseline_run_id}")
    table.add_column("Variation", style="cyan")
    table.add_column("Hours", justify="right")
    table.add_column("Cost (GBP)", justify="right")
    table.add_column("Timeline", justify="right")
    table.add_column("Run", style="dim")

    for var_name, var_path in sorted(variations, key=lambda x: (x[0] or "unnamed")):
        prop_path = var_path / "proposal.json"
        if not prop_path.exists():
            table.add_row(var_name or "unnamed", "-", "-", "-", var_path.name)
            continue
        doc = ProposalDocument.model_validate_json(prop_path.read_text())
        total_h = doc.total_estimated_hours or sum(p.estimated_hours for p in doc.delivery_phases)
        total_c = sum(p.estimated_cost_gbp or 0 for p in doc.delivery_phases)
        weeks = doc.total_estimated_weeks or doc.timeline_weeks or 0
        table.add_row(
            var_name or "unnamed",
            f"{total_h:.0f}h",
            f"£{total_c:,.0f}",
            f"{weeks}w",
            var_path.name,
        )
    console.print(table)


if __name__ == "__main__":
    main()
