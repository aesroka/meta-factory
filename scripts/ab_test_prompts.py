#!/usr/bin/env python3
"""A/B test prompt variants (Phase 13).

Usage:
  python scripts/ab_test_prompts.py --agent discovery --variants default,concise --input workspace/sample_transcript.txt --client Test
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    try:
        import click
    except ImportError:
        print("Install click: pip install click")
        sys.exit(1)

    @click.command()
    @click.option("--agent", default="discovery", help="Agent role (discovery, etc.)")
    @click.option("--variants", default="default,concise", help="Comma-separated variant names")
    @click.option("--input", "input_path", required=True, type=click.Path(exists=True), help="Input transcript file")
    @click.option("--client", default="AB-Test-Client", help="Client name")
    @click.option("--max-cost", type=float, default=2.0, help="Max cost per variant run (USD)")
    def run(agent: str, variants: str, input_path: str, client: str, max_cost: float) -> None:
        variant_list = [v.strip() for v in variants.split(",") if v.strip()]
        content = Path(input_path).read_text()
        from utils.ab_test import run_ab_test
        report = run_ab_test(agent, variant_list, content, client, max_cost_per_run=max_cost)
        md = report.to_markdown()
        print(md)
        out_dir = REPO_ROOT / "outputs"
        out_dir.mkdir(exist_ok=True)
        report_path = out_dir / f"ab_test_{agent}.md"
        report_path.write_text(md)
        print(f"\nReport saved to {report_path}")

    run()


if __name__ == "__main__":
    main()
