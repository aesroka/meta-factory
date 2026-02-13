# Phase 6 Completion Note: Hybrid Context Strategy

**Completed:** 2025-02-12

## What was done

- **6.1** Tier0 ("Oracle") added to `providers/router.py` (gemini-2.5-pro, claude-opus-4); `LiteLLMProvider` recognises `"tier0"` and routes through Router.
- **6.2** `IngestionInput`: added `context_mode: str = "rag"` and `raw_documents: Optional[str]`. `IngestionSwarm.execute()` branches: `rag` → `_run_rag_pipeline()`; `full` → `_full_context_extract()`; `hybrid` → both + `_reconcile_dossiers()`.
- **6.3** `contracts/reconciliation.py`: `DossierReconciliation` (merged_dossier, agreements, disagreements, rag_only_items, full_context_only_items, confidence_score). `_reconcile_dossiers()` implements heuristic merge (union of stakeholders, tech, constraints, flows; agreements/rag_only/full_only from set comparison). No LLM reconciler yet.
- **6.4** `Librarian`: `library_dir` in __init__; `get_context_for_agent(agent_role, depth="cheat_sheet")`; `_combine_from_library()` for depth `"full"` (falls back to cheat sheet if file missing). `BaseAgent`: optional `depth` param; `_context_depth` derived from `DEFAULT_TIER` (tier0/tier3 → "full", else "cheat_sheet"); `_load_bible_context()` passes depth to Librarian.
- **6.5** CLI: `--context-mode rag|full|hybrid` and `--quality standard|premium` on `showcase_forge_stream.py` and `rag_agent_demo.py`. `--quality premium` sets context_mode to hybrid. `rag_agent_demo` builds `raw_documents` from workspace when context_mode is full/hybrid and passes to `IngestionInput`.
- **6.6** `tests/test_hybrid_context.py`: reconciliation contract, IngestionInput default context_mode, router tier0, provider tier0 in source.

## Gotchas

- **Full-context / hybrid require `raw_documents`.** If `context_mode` is full or hybrid and `raw_documents` is None/empty, execute() returns error. Demo script builds it from workspace files.
- **Reconciliation is heuristic.** Plan mentioned an LLM (tier2) reconciler; current implementation is set-based merge. LLM step can be added later for richer disagreement notes.
- **Library dir:** `library/` may not contain full Bible texts; plan says "document which need to be added". `_combine_from_library` falls back to cheat sheet when a file is missing.

## Debt / follow-ups

- Add LLM-based reconciliation step (tier2) for hybrid to produce narrative agreements/disagreements.
- Make tier0 model list configurable (like other tiers).
- E2E test hybrid with real RAG + raw_documents (needs RAGFlow or mock).

## Reviewer checklist

- [ ] Run `pytest tests/test_hybrid_context.py -v`.
- [ ] Run `python scripts/rag_agent_demo.py --mode dossier --no-sync` (RAG-only) and `--context-mode hybrid` with workspace files present.
- [ ] Confirm `get_context_for_agent(role, depth="full")` uses library/ when directory exists.
