#!/usr/bin/env python3
"""Forge-Stream end-to-end showcase: Dossier → Discovery → … → Proposal.

Runs the Phase 4 pipeline without RAGFlow: a curated ProjectDossier (built from
workspace/sample_transcript.txt + sample_notes.txt) is fed into GreenfieldSwarm.
Experts (Discovery, Architect, Estimator, Synthesis) work from the dossier,
not raw text.

Usage:
  python scripts/showcase_forge_stream.py              # Full pipeline (needs LLM API key)
  python scripts/showcase_forge_stream.py --dry-run    # Adapter + transcript only, no LLM
  python scripts/showcase_forge_stream.py -p gemini   # Use Gemini

For RAG-backed run (sync workspace → Miner → Dossier → Greenfield) use:
  python scripts/rag_agent_demo.py --mode full-dossier
For cost comparison (raw vs dossier path): python scripts/rag_agent_demo.py --compare
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _banner(title: str, width: int = 64) -> None:
    print()
    print("╔" + "═" * (width - 2) + "╗")
    mid = title.center(width - 2)
    print("║" + mid + "║")
    print("╚" + "═" * (width - 2) + "╝")
    print()


def _step(n: int, title: str, body: str) -> None:
    print(f"  ┌─ Step {n}: {title}")
    print("  │")
    for line in body.strip().splitlines():
        print("  │  " + line)
    print("  └" + "─" * 60)
    print()


def build_curated_dossier(workspace_dir: Path):
    """Build a ProjectDossier from workspace sample files (simulates Miner output)."""
    from contracts import (
        ProjectDossier,
        Stakeholder,
        TechConstraint,
        CoreLogicFlow,
    )

    transcript_path = workspace_dir / "sample_transcript.txt"
    notes_path = workspace_dir / "sample_notes.txt"
    summary_parts = []
    if transcript_path.exists():
        summary_parts.append(
            "Acme Logistics runs discovery with drivers and dispatchers. "
            "Pain: paper manifests printed daily; route changes require reprint and drivers sometimes leave before updates. "
            "Desired state: driver opens app, sees live manifest that updates when routes change; no paper; digital audit trail."
        )
    if notes_path.exists():
        summary_parts.append(
            "Tech stack: React Native mobile, Java/Spring Boot backend, JWT auth. "
            "Gaps: no WebSocket/push for live manifest updates; app assumes fixed manifest at login; offline is partial. "
            "Legacy routing service has no event API—polling or adapter may be needed."
        )
    summary = " ".join(summary_parts) if summary_parts else "Logistics field app modernization."

    return ProjectDossier(
        project_name="Acme Logistics – Field App",
        summary=summary,
        stakeholders=[
            Stakeholder(name="Alex", role="Product", concerns=["paper manifests", "route updates", "compliance", "audit trail"]),
            Stakeholder(name="Sam", role="Engineering", concerns=["dynamic manifest refresh", "mobile app", "offline support"]),
            Stakeholder(name="Jordan", role="Consultant", concerns=["real-time updates", "reducing paper-based errors"]),
        ],
        tech_stack_detected=["React Native", "Java", "Spring Boot", "REST API", "JWT", "routing service"],
        constraints=[
            TechConstraint(category="Mobile", requirement="Real-time manifest updates; offline-capable", priority="Must-have"),
            TechConstraint(category="Compliance", requirement="Digital records for auditors", priority="Must-have"),
            TechConstraint(category="Backend", requirement="WebSocket or push channel for manifest stream", priority="Should-have"),
        ],
        logic_flows=[
            CoreLogicFlow(trigger="Driver opens app", process="Subscribe to route updates; load manifest", outcome="Live manifest displayed"),
            CoreLogicFlow(trigger="Dispatcher changes route", process="Routing service publishes; backend fans out", outcome="Connected drivers receive update"),
        ],
        legacy_debt_summary="Routing service has no event API; may need polling or small adapter. App assumes manifest fixed at login; no refresh.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forge-Stream showcase: Dossier → Greenfield pipeline (no RAGFlow)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only run adapter and print discovery transcript; no LLM calls.",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["openai", "gemini", "deepseek", "anthropic"],
        default="openai",
        help="LLM provider (default: openai).",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model override (e.g. gpt-4o-mini).",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=5.0,
        help="Max cost USD (default: 5.0).",
    )
    args = parser.parse_args()

    workspace_dir = REPO_ROOT / "workspace"
    if not workspace_dir.is_dir():
        print("[ERROR] workspace/ not found.")
        sys.exit(1)

    _banner("Forge-Stream Showcase: Dossier-Primed Pipeline", 64)

    print("  This run uses a curated ProjectDossier (from workspace samples)")
    print("  instead of raw RAG transcript. Experts see structured context.")
    print()

    # --- Step 1: "Dossier" (curated) ---
    dossier = build_curated_dossier(workspace_dir)
    _step(
        1,
        "Dossier (as if from Miner)",
        f"project_name: {dossier.project_name}\n"
        f"stakeholders: {[s.name for s in dossier.stakeholders]}\n"
        f"tech_stack: {dossier.tech_stack_detected}\n"
        f"constraints: {len(dossier.constraints)}; logic_flows: {len(dossier.logic_flows)}"
    )
    print("  Full dossier (excerpt):")
    dumped = dossier.model_dump()
    print("  " + json.dumps({k: (v if k != "summary" else v[:200] + "...") for k, v in dumped.items()}, indent=4, default=str).replace("\n", "\n  "))
    print()

    # --- Step 2: Adapter ---
    from contracts.adapters import dossier_to_discovery_input

    discovery_input = dossier_to_discovery_input(dossier)
    transcript = discovery_input.transcript
    _step(
        2,
        "Adapter: dossier → DiscoveryInput",
        f"Transcript length: {len(transcript)} chars (structured markdown)"
    )
    print("  Transcript preview:")
    for line in transcript.splitlines()[:25]:
        print("  │  " + line)
    if transcript.count("\n") > 25:
        print("  │  ...")
    print()

    if args.dry_run:
        print("  [--dry-run] Skipping Greenfield pipeline. Done.")
        print()
        return

    # --- Step 3: Greenfield pipeline (real LLM) ---
    from config import settings
    from providers import get_provider
    from librarian.librarian import Librarian
    from orchestrator.cost_controller import reset_cost_controller
    from swarms import GreenfieldSwarm, GreenfieldInput
    from providers.cost_logger import get_swarm_cost_logger

    provider = get_provider(args.provider, args.model)
    if not provider.is_available():
        print(f"  [ERROR] Provider '{args.provider}' not configured. Set API key in .env or use --dry-run.")
        sys.exit(1)

    _step(
        3,
        "Greenfield pipeline (Dossier → Discovery → Architect → Estimator → Synthesis → Proposal)",
        f"Provider: {args.provider}, model: {provider.default_model or 'default'}"
    )

    reset_cost_controller(args.max_cost)
    lib = Librarian()
    swarm = GreenfieldSwarm(
        librarian=lib,
        run_id="showcase_forge_stream",
        provider=args.provider,
        model=args.model,
    )
    try:
        result = swarm.execute(GreenfieldInput(client_name="Acme Logistics", dossier=dossier))
    except Exception as e:
        print(f"  [ERROR] Pipeline failed: {e}")
        raise

    status = result.get("status", "unknown")
    cost = get_swarm_cost_logger().total_cost
    print("  Pipeline result:")
    print(f"    status: {status}")
    print(f"    cost:   ${cost:.4f}")
    if result.get("error"):
        print(f"    error:  {result['error']}")
    print()

    artifacts = result.get("artifacts", {})
    if artifacts.get("proposal"):
        doc = artifacts["proposal"]
        if hasattr(doc, "model_dump"):
            doc = doc.model_dump()
        exec_summary = doc.get("executive_summary") or doc.get("summary")
        if exec_summary:
            text = exec_summary.get("narrative", str(exec_summary)) if isinstance(exec_summary, dict) else str(exec_summary)
            print("  Proposal (excerpt):")
            print("  " + "─" * 56)
            for line in (text[:1200] + "..." if len(text) > 1200 else text).splitlines():
                print("  " + line)
    elif artifacts:
        print("  Artifacts produced:", ", ".join(artifacts.keys()))
    print()
    print("  Artifacts written to:", result.get("output_path", "outputs/"))
    print()
    _banner("Done. Experts ran from Dossier, not raw transcript.", 64)


if __name__ == "__main__":
    main()
