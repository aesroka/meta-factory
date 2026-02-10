# Project: Forge-Stream — Implementation Roadmap

Plan to integrate **meta-factory** with **RAGFlow** and a **Cascading Model Architecture**.

RAGFlow moves "upstream" as the primary ingestion engine for client transcripts, existing codebases, and technical documentation, so even Discovery agents are not overwhelmed by raw data.

---

## Developer Intent & Guardrails

**Intent:** Refactor `meta-factory` to use a **Modular RAG Ingestion Layer** (via RAGFlow) and an **Intelligence-Tiered Execution Layer** (via LiteLLM).

| Rule | Description |
|------|-------------|
| **Rule 1** | No agent reads a raw file. Every agent interacts with the **Librarian** (RAG) or a **Dossier** (Compressed JSON). |
| **Rule 2** | Use **Tier 1 (Cheap)** models for all extraction/mapping and **Tier 3 (Expensive)** only for final synthesis and critical reviews. |
| **Validation** | All cross-tier data must validate against `contracts/` Pydantic models. |

---

## Codebase Notes (read before implementing)

These are the actual file paths and conventions in the existing repo — any references below have been corrected to match.

| Concern | Actual location |
|---------|----------------|
| Critic agent | `agents/critic_agent.py` (NOT `orchestrator/critic.py`) |
| Cost controller / circuit breaker | `orchestrator/cost_controller.py` |
| Existing swarms | `swarms/greenfield.py`, `swarms/brownfield.py`, `swarms/greyfield.py` (no `consultancy_swarm.py` yet) |
| Provider layer | `providers/` — already supports Anthropic, OpenAI, Gemini, Deepseek via `get_provider()` |
| Critic score scale | **0.0–1.0** with pass threshold `0.7` (set in `config.py` as `critic_pass_score`) |
| Default model | `claude-sonnet-4-20250514` (set in `config.py`) |
| `agents/tools/` | Directory does not exist yet — must be created in Phase 1 |

---

## Implementation Checklist

### Phase 0: Pydantic Contract Definition

*Before any logic is written, define the "Truth" that Tier 1 must produce for Tier 3.*

- [x] **Contract Definition:** Add `ProjectDossier` and related models to `contracts/project.py`.
  - `Stakeholder` (name, role, concerns)
  - `TechConstraint` (category, requirement, priority)
  - `CoreLogicFlow` (trigger, process, outcome)
  - `ProjectDossier` (project_name, summary, stakeholders, tech_stack_detected, constraints, logic_flows, legacy_debt_summary)

---

### Phase 1: Ingestion Infrastructure (The RAG Pipeline)

*Goal: Use RAGFlow for all information gathering (reading transcripts, repos, and docs).*

- [x] **Add SDK / HTTP:** Add `requests` to `requirements.txt` for RAGFlow HTTP API (optional `ragflow-sdk` when on Python ≥3.12).
- [x] **RAG Client:** Create `librarian/rag_client.py` — wrapper over RAGFlow (SDK when available, else HTTP) for connection, dataset management, upload, and parsing status.
- [x] **Librarian Refactor:** Update `librarian/librarian.py` to include `sync_workspace()`:
  - Recursively scan the `workspace/` folder.
  - Upload new transcripts, docs, and code files to a RAGFlow "Dataset" via `rag_client`.
  - Trigger RAGFlow's "Deep Document Understanding" (DDU) parsing.
  - `get_rag_passages()` wired to RAG client (returns [] when RAG not configured).
- [x] **RAG Tooling:** Create `agents/tools/` directory and `agents/tools/rag_search.py`, allowing agents to query RAGFlow datasets with similarity thresholds.
- [x] **Config Update:** Add RAGFlow settings to `config.py` and `.env` placeholders.
- [x] **Test:** Create `tests/test_rag_client.py` — client, sync_workspace, rag_search, get_rag_passages (mocked; no live RAGFlow required).

---

### Phase 2: Model Cascading (The Intelligence Router)

*Goal: Dynamically swap models based on task complexity; hard-wire cost-saving logic into agent definitions.*

- [ ] **LiteLLM Integration:** Add `litellm` to `requirements.txt`. Decide integration approach:
  - **Option A:** Add a `LiteLLMProvider` to `providers/` that wraps LiteLLM's `completion()`, keeping the existing `LLMProvider` interface.
  - **Option B:** Replace the existing provider layer entirely with LiteLLM.
  - Recommendation: **Option A** — least disruptive, existing tests keep passing.
- [ ] **Config Setup:** Add `MODEL_TIERS` to `config.py` with current model identifiers:
  - `TIER_1_MINER`: `gemini-1.5-flash` or `gpt-4o-mini`.
  - `TIER_2_CRITIC`: `claude-3-5-haiku-20241022` (or latest haiku).
  - `TIER_3_EXPERT`: `claude-sonnet-4-20250514` (current default) or `gpt-4o`.
- [ ] **BaseAgent Update:** Modify `agents/base_agent.py` to accept a `tier` argument. Map tier to the correct model from `MODEL_TIERS`, falling back to existing `provider`/`model` if no tier is set.
- [ ] **Cost Tracking:** Log `model_name`, `tier`, and `cost_estimate` in the terminal for every agent turn (use Rich console, not bare `print`).

---

### Phase 3: The "Miner" Swarm (Compaction)

*Goal: Turn RAG results into the `ProjectDossier` JSON using Tier 1 models.*

- [ ] **Miner Agent:** Create `agents/miner_agent.py` using **Tier 1**. Loop through RAGFlow chunks and populate the `ProjectDossier`.
- [ ] **Swarm Logic:** Implement `swarms/ingestion_swarm.py`:
  - One agent processes business transcripts.
  - One agent processes technical documentation/repos.
  - One "Aggregator" agent combines results into the final `ProjectDossier`.
  - Register in `swarms/__init__.py`.
- [ ] **Verify:** Run the ingestion swarm on a sample project (use `demo/` data). Output should be a single, clean `dossier.json` in `outputs/`.

---

### Phase 4: Expert Synthesis (The Final Artifact)

*Goal: Expert models work ONLY from the Dossier + targeted RAG queries.*

- [ ] **Expert Agent Update:** Modify the existing swarms (`swarms/greenfield.py`, `swarms/brownfield.py`, `swarms/greyfield.py`) so the pipeline accepts a `ProjectDossier` as primary input instead of raw content. Alternatively, create a new `swarms/consultancy_swarm.py` that wraps Dossier-first logic and delegates to the existing swarm stages.
- [ ] **JIT RAG Access:** Allow Expert Agents (Tier 3) to call `rag_search` *only* if the `ProjectDossier` is insufficient.
- [ ] **Verify:** Measure total token usage vs. the old "Full Document" method. Dossier-Primed run should be >50% cheaper.

---

### Phase 5: Quality Gate (The Critic Loop)

*Goal: Tier 2 validates; Tier 3 fixes if needed.*

- [ ] **Critic Tier Assignment:** Update `agents/critic_agent.py` to default to **Tier 2** model. When critic fails an artifact (score < `critic_pass_score`, currently 0.7), hand off to a **Tier 3** Expert for refinement instead of re-running the same agent.
- [ ] **Cost Circuit Breaker:** Update `orchestrator/cost_controller.py`:
  - Add a `cost_warning_threshold` (default 0.8, i.e. 80% of budget).
  - When `total_cost_usd >= max_cost_usd * cost_warning_threshold`, force all subsequent agent calls to Tier 1.
  - Existing hard cutoff at 100% remains for full stop.
- [ ] **Final Acceptance Test:** End-to-end project run using Greenfield + Brownfield inputs from `demo/`.

---

## Instructions for Cursor / Claude Code

1. **Start with Phase 1.** Phase 0 is complete. Do not proceed to Phase 2 until the Librarian can successfully talk to a RAGFlow instance.
2. **Strict Mode:** If a Tier 1 agent produces malformed JSON that fails the Pydantic check, it must retry *once* before the Orchestrator escalates it to Tier 2. (Note: `BaseAgent.run()` already supports `max_retries`; wire this into the tier escalation logic in Phase 2.)
3. **Test early:** Each phase should have at least one test in `tests/` before moving on.

---

## Next Step

> Start with **Phase 1**. Create `librarian/rag_client.py` (RAGFlow SDK wrapper) and `tests/test_rag_client.py` that can upload a single text file and poll for the parsing status.
