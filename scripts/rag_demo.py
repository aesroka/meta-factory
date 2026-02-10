#!/usr/bin/env python3
"""End-to-end RAGFlow demo: sync workspace to RAGFlow, then run example searches.

Run from repo root with venv activated:

    python scripts/rag_demo.py

Prerequisites:
  - RAGFlow running (see docs/RAGFLOW_SETUP.md)
  - META_FACTORY_RAGFLOW_API_KEY and META_FACTORY_RAGFLOW_API_URL set in .env
  - Some files in workspace/ (e.g. workspace/sample_transcript.txt, sample_notes.txt)
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

# Suppress urllib3/OpenSSL warning on macOS (LibreSSL vs OpenSSL)
warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*", module="urllib3")

# Run from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    from config import settings
    from librarian.librarian import Librarian, WORKSPACE_SYNC_EXTENSIONS
    from agents.tools.rag_search import rag_search

    print("=" * 60)
    print("RAGFlow end-to-end demo (meta-factory)")
    print("=" * 60)

    if not settings.ragflow_api_key:
        print("\n[ERROR] META_FACTORY_RAGFLOW_API_KEY is not set.")
        print("Add it to .env (see docs/RAGFLOW_SETUP.md).")
        sys.exit(1)

    # Resolve workspace to repo root so we find files regardless of cwd
    workspace_dir = (REPO_ROOT / "workspace").resolve()
    print(f"\nRAGFlow URL: {settings.ragflow_api_url}")
    print(f"Workspace:   {workspace_dir}")
    print(f"Dataset:     {settings.ragflow_dataset_name}")

    # Show which files we'll sync (same rules as Librarian)
    to_sync = [
        p for p in sorted(workspace_dir.rglob("*"))
        if p.is_file() and p.suffix.lower() in WORKSPACE_SYNC_EXTENSIONS
    ]
    print(f"Files to sync: {len(to_sync)}")
    for p in to_sync:
        print(f"  - {p.name}")
    if not to_sync:
        print("  (none – add .txt/.md etc. under workspace/ and run again)")
        sys.exit(0)

    # 1) Sync workspace → RAGFlow
    print("\n--- Step 1: Sync workspace to RAGFlow ---")
    lib = Librarian()
    try:
        # Wait up to 90s for parsing so demo completes in reasonable time
        result = lib.sync_workspace(
            workspace_dir=workspace_dir,
            wait_parsed=True,
            parse_timeout_sec=90.0,
        )
    except Exception as e:
        print(f"[ERROR] sync_workspace failed: {e}")
        sys.exit(1)

    uploaded = result.get("uploaded_count", 0)
    doc_ids = result.get("document_ids", [])
    dataset_id = result.get("dataset_id")

    if uploaded == 0:
        print("Upload failed or no files were uploaded. Check errors above.")
        sys.exit(1)

    print(f"Uploaded: {uploaded} file(s)")
    print(f"Dataset ID: {dataset_id}")
    if doc_ids:
        print(f"Document IDs: {doc_ids[:5]}{'...' if len(doc_ids) > 5 else ''}")
    if result.get("parse_results"):
        print("Parsing: completed (DDU)")
    print("Verify: http://127.0.0.1 → Knowledge Base → open the dataset with ID above (or name meta-factory-workspace-...)")

    # 2) Example searches
    print("\n--- Step 2: Example searches (top 5 chunks each) ---")
    queries = [
        "What is the main pain point for drivers and dispatchers?",
        "What does the tech stack look like?",
        "What would success look like for the client?",
    ]
    any_chunks = False
    for q in queries:
        print(f"\nQuery: \"{q}\"")
        chunks = rag_search(q, dataset_id=dataset_id, top_k=5)
        if not chunks:
            print("  (no chunks returned)")
            continue
        any_chunks = True
        for i, c in enumerate(chunks, 1):
            content = (c.get("content") or "").strip()
            sim = c.get("similarity")
            preview = content[:200] + "..." if len(content) > 200 else content
            sim_str = f" (similarity={sim:.2f})" if sim is not None else ""
            print(f"  [{i}]{sim_str}")
            print(f"      {preview}")

    if not any_chunks:
        print("\n  (If retrieval always returns no chunks, check RAGFlow Settings / dataset embedding model.)")

    print("\n" + "=" * 60)
    print("Done. Agents can use rag_search() or Librarian.get_rag_passages() with this dataset.")
    print("")
    print("Verify in RAGFlow UI: http://127.0.0.1 → Knowledge Base → your dataset (e.g. meta-factory-workspace-xxxx)")
    print("=" * 60)


if __name__ == "__main__":
    main()
