#!/usr/bin/env python3
"""Demo: agents using RAGFlow as part of their workflow.

1. Syncs workspace to RAGFlow (if needed).
2. Retrieves context via RAG for discovery-relevant queries.
3. Runs the Discovery agent (and optionally the full greenfield pipeline)
   with that RAG-sourced context as the "transcript".

So the agent's input comes from RAG, not from a raw file — demonstrating
the Forge-Stream rule: agents interact with the Librarian (RAG), not raw files.

Usage:
  python scripts/rag_agent_demo.py                    # Discovery only, OpenAI (default)
  python scripts/rag_agent_demo.py --full             # Full greenfield pipeline
  python scripts/rag_agent_demo.py -p gemini         # Use Gemini
  python scripts/rag_agent_demo.py -p deepseek       # Use Deepseek
  python scripts/rag_agent_demo.py --no-sync         # Skip sync (use existing dataset)
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

# Suppress urllib3/OpenSSL warning on macOS
warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*", module="urllib3")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# RAG queries used to build the "transcript" the agent will see
RAG_QUERIES = [
    "What are the main pain points for drivers and dispatchers?",
    "What does the tech stack look like?",
    "What would success look like for the client?",
    "What constraints or requirements were mentioned?",
]


def build_rag_transcript(rag_search_fn, dataset_id: str | None, top_k: int = 5) -> str:
    """Build a single transcript-like string from RAG search results."""
    sections = []
    for q in RAG_QUERIES:
        chunks = rag_search_fn(q, dataset_id=dataset_id, top_k=top_k)
        if not chunks:
            continue
        parts = [f"## From workspace (query: {q!r})\n"]
        for i, c in enumerate(chunks, 1):
            content = (c.get("content") or "").strip()
            sim = c.get("similarity")
            if sim is not None:
                parts.append(f"[{i}] (similarity={sim:.2f})\n{content}\n\n")
            else:
                parts.append(f"[{i}]\n{content}\n\n")
        sections.append("".join(parts))
    if not sections:
        return ""
    return "\n---\n\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo agents using RAGFlow: RAG context → Discovery (and optionally full pipeline)."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full greenfield pipeline (Discovery → … → Proposal). Default: Discovery only.",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip workspace sync; use existing RAGFlow dataset (must have been synced earlier).",
    )
    parser.add_argument(
        "--client",
        default="Acme Logistics",
        help="Client name for the proposal (default: Acme Logistics).",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=5.0,
        help="Max cost in USD for the run (default: 5.0).",
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["openai", "gemini", "deepseek", "anthropic"],
        default="openai",
        help="LLM provider (default: openai). Use openai, gemini, or deepseek if you don't have Anthropic.",
    )
    parser.add_argument(
        "--model", "-m",
        default=None,
        help="Model name (e.g. gpt-4o, gemini-1.5-flash, deepseek-chat). Default depends on provider.",
    )
    args = parser.parse_args()

    from config import settings
    from librarian.librarian import Librarian, WORKSPACE_SYNC_EXTENSIONS
    from agents.tools.rag_search import rag_search
    from orchestrator import EngagementManager
    from contracts import Mode

    print("=" * 60)
    print("RAG + Agents demo (meta-factory)")
    print("=" * 60)

    if not settings.ragflow_api_key:
        print("\n[ERROR] META_FACTORY_RAGFLOW_API_KEY is not set. Add it to .env.")
        sys.exit(1)

    workspace_dir = (REPO_ROOT / "workspace").resolve()
    lib = Librarian()
    dataset_id = None

    # --- Step 1: Sync workspace to RAGFlow (unless --no-sync) ---
    if not args.no_sync:
        print("\n--- Step 1: Sync workspace to RAGFlow ---")
        to_sync = [
            p for p in sorted(workspace_dir.rglob("*"))
            if p.is_file() and p.suffix.lower() in WORKSPACE_SYNC_EXTENSIONS
        ]
        if not to_sync:
            print("No files to sync in workspace/. Add .txt/.md etc. and run again.")
            sys.exit(1)
        try:
            result = lib.sync_workspace(
                workspace_dir=workspace_dir,
                wait_parsed=True,
                parse_timeout_sec=90.0,
            )
            dataset_id = result.get("dataset_id")
            print(f"Synced {result.get('uploaded_count', 0)} file(s), dataset_id={dataset_id}")
        except Exception as e:
            print(f"[ERROR] sync_workspace failed: {e}")
            sys.exit(1)
    else:
        print("\n--- Step 1: Skip sync (--no-sync); using existing dataset ---")
        from librarian.rag_client import RAGFlowClient
        client = RAGFlowClient()
        if client.is_available():
            dataset_id = client.ensure_dataset()
            print(f"Using dataset_id={dataset_id}")
        else:
            print("[WARN] RAGFlow client not available; RAG context may be empty.")

    # --- Step 2: Build transcript from RAG retrieval ---
    print("\n--- Step 2: Retrieve context from RAGFlow ---")
    rag_transcript = build_rag_transcript(rag_search, dataset_id, top_k=5)
    if not rag_transcript:
        print("[WARN] No RAG chunks returned. Check RAGFlow embedding model and dataset.")
        print("Using a short placeholder so the agent still runs.")
        rag_transcript = (
            "No workspace content was retrieved from RAG. "
            "Ensure workspace is synced and retrieval returns chunks."
        )
    else:
        print(f"Built transcript from {len(RAG_QUERIES)} RAG queries ({len(rag_transcript)} chars).")

    # --- Step 3: Run agent(s) with RAG-sourced "transcript" ---
    print("\n--- Step 3: Run agent(s) with RAG-sourced input ---")
    print(f"Provider: {args.provider}" + (f", model: {args.model}" if args.model else ""))
    print("(The agent's 'transcript' is the context retrieved above from RAGFlow.)\n")

    if args.full:
        # Full greenfield pipeline (Discovery → Architect → … → Proposal)
        manager = EngagementManager(
            max_cost_usd=args.max_cost,
            output_dir=REPO_ROOT / "outputs",
            provider=args.provider,
            model=args.model,
        )
        try:
            result = manager.run(
                input_content=rag_transcript,
                client_name=args.client,
                force_mode=Mode.GREENFIELD,
                provider=args.provider,
                model=args.model,
            )
        except Exception as e:
            print(f"[ERROR] Run failed: {e}")
            raise
        status = result.get("status", "unknown")
        print(f"\nRun status: {status}")
        artifacts = result.get("artifacts", {})
        if artifacts.get("proposal"):
            print("\nProposal (excerpt):")
            doc = artifacts["proposal"]
            if hasattr(doc, "model_dump"):
                doc = doc.model_dump()
            exec_summary = doc.get("executive_summary") or doc.get("summary")
            if exec_summary:
                text = exec_summary.get("narrative", str(exec_summary)) if isinstance(exec_summary, dict) else str(exec_summary)
                print(text[:800] + "..." if len(text) > 800 else text)
        print("\nFull artifacts in:", result.get("output_dir", "outputs/"))
    else:
        # Discovery only: run Discovery agent with RAG transcript (fast, cheap)
        from swarms import GreenfieldSwarm, GreenfieldInput
        from orchestrator.cost_controller import reset_cost_controller
        reset_cost_controller(args.max_cost)
        swarm = GreenfieldSwarm(
            librarian=lib,
            run_id="rag_agent_demo",
            provider=args.provider,
            model=args.model,
        )
        swarm_input = GreenfieldInput(transcript=rag_transcript, client_name=args.client)
        try:
            pain_matrix = swarm._run_discovery(swarm_input)
        except Exception as e:
            print(f"[ERROR] Discovery failed: {e}")
            raise
        print("\nDiscovery output (Pain-Monetization Matrix from RAG context):")
        if hasattr(pain_matrix, "model_dump"):
            print(json.dumps(pain_matrix.model_dump(), indent=2, default=str))
        else:
            print(json.dumps(pain_matrix, indent=2, default=str))

    print("\n" + "=" * 60)
    print("Done. Agents used RAGFlow-retrieved context as their input.")
    print("=" * 60)


if __name__ == "__main__":
    main()
