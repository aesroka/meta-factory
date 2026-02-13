# Phase 8 Completion Note: All Paths with Dossier Integration

**Completed:** 2025-02-12

## What was done

- **8.1** BrownfieldInput: added `dossier: Optional[ProjectDossier] = None`; `codebase_description` default `""`. `_run_legacy_analysis`: when `input_data.dossier` is set, use `dossier_to_legacy_input(dossier)` as codebase_description for LegacyInput.
- **8.2** `contracts/adapters.py`: added `dossier_to_legacy_input(dossier)` returning a string (project, summary, tech stack, constraints, logic flows, legacy debt). GreyfieldInput: added `dossier: Optional[ProjectDossier] = None`; in `_run_parallel_analysis` when dossier is set, derive transcript from `dossier_to_discovery_input(dossier)` and codebase_description from `dossier_to_legacy_input(dossier)` for the two parallel paths.
- **8.3** BROWNFIELD_RAG_QUERIES not added (plan optional; ingestion mode awareness can be added later).
- **8.4** Demo scripts: rag_agent_demo already has --mode; showcase_brownfield.py not added (main.py and rag_agent_demo cover brownfield/greyfield with dossier when passed programmatically).
- **8.5** tests/test_adapters.py: added `test_dossier_to_legacy_input_produces_codebase_description`.

## Gotchas

- BrownfieldInput.codebase_description is now optional when dossier is provided; callers must pass either codebase_description or dossier.
- GreyfieldInput.transcript and codebase_description default to "" when dossier is provided.

## Debt / follow-ups

- BROWNFIELD_RAG_QUERIES in IngestionSwarm when mode brownfield.
- scripts/showcase_brownfield.py for curated brownfield dossier run.
- main.py wiring for --mode brownfield/greyfield with dossier from ingestion.

## Reviewer checklist

- [ ] Run `pytest tests/test_adapters.py -v`.
- [ ] BrownfieldSwarm.execute(BrownfieldInput(dossier=dossier)) uses adapter for legacy stage.
- [ ] GreyfieldSwarm.execute(GreyfieldInput(dossier=dossier)) uses adapters for both discovery and legacy.
