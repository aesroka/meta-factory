# Project: Forge-Stream — Implementation Roadmap

Plan to integrate **meta-factory** with **RAGFlow** and a **Cascading Model Architecture**.

RAGFlow moves "upstream" as the primary ingestion engine for client transcripts, existing codebases, and technical documentation, so even Discovery agents are not overwhelmed by raw data.

---

## Developer Intent & Guardrails

**Intent:** Refactor `meta-factory` to use a **Modular RAG Ingestion Layer** (via RAGFlow) and an **Intelligence-Tiered Execution Layer** (via LiteLLM Router).

| Rule | Description |
|------|-------------|
| **Rule 1** | No agent reads a raw file. Every agent interacts with the **Librarian** (RAG) or a **Dossier** (Compressed JSON). |
| **Rule 2** | Use **Tier 1 (Cheap)** models for all extraction/mapping and **Tier 3 (Expensive)** only for final synthesis and critical reviews. |
| **Rule 3** | Cost tracking, retries, fallbacks, and budget enforcement are LiteLLM's job, not ours. Do not reimplement what LiteLLM provides. |
| **Validation** | All cross-tier data must validate against `contracts/` Pydantic models. |

---

## Codebase Notes (read before implementing)

These are the actual file paths and conventions in the existing repo.

| Concern | Actual location |
|---------|----------------|
| Critic agent | `agents/critic_agent.py` |
| Cost controller / circuit breaker | `orchestrator/cost_controller.py` |
| Existing swarms | `swarms/greenfield.py`, `swarms/brownfield.py`, `swarms/greyfield.py` |
| Provider layer | `providers/` — **to be replaced by LiteLLM in Phase 2** |
| Base agent | `agents/base_agent.py` — `__init__` takes `provider`/`model`, calls `get_provider()`, stores `self.llm_provider` |
| Critic loop | `swarms/base_swarm.py` `run_with_critique()` — sequential review, enriched re-run on fail |
| RAG client | `librarian/rag_client.py` — HTTP fallback (SDK path exists but untested) |
| RAG search tool | `agents/tools/rag_search.py` — `rag_search(query, dataset_id, top_k)` |
| Config | `config.py` — pydantic-settings, `META_FACTORY_` prefix, `.env` loaded at import |
| Critic score scale | **0.0–1.0**, pass threshold `0.7` (`config.py: critic_pass_score`) |
| Default model | `claude-sonnet-4-20250514` (`config.py`) |
| Demo scripts | `scripts/rag_demo.py` (RAG only), `scripts/rag_agent_demo.py` (RAG + agent pipeline) |

### LiteLLM model naming (use these exact strings)

LiteLLM uses `provider/model-name` format. OpenAI models can optionally omit the prefix.

| Provider | LiteLLM model string | Notes |
|----------|---------------------|-------|
| OpenAI | `gpt-4o`, `gpt-4o-mini` | Prefix optional for OpenAI |
| Anthropic | `anthropic/claude-sonnet-4-20250514`, `anthropic/claude-3-5-haiku-20241022` | Prefix required |
| Gemini | `gemini/gemini-2.0-flash`, `gemini/gemini-2.5-flash`, `gemini/gemini-2.5-pro` | Prefix required |
| Deepseek | `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner` | Prefix required |

**Do not use deprecated model IDs** like `gemini-1.5-flash`, `gemini-1.5-pro`, or `gemini-2.0-flash-exp`. They 404.

LiteLLM reads API keys from standard env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`. These are already in our `.env` — no `META_FACTORY_` prefix needed for LLM keys.

---

## RAGFlow Operational Notes

These are hard-won from debugging. **Read before touching RAGFlow code.**

| What | Detail |
|------|--------|
| **RAGFlow version** | v0.23.1 (pinned in `ragflow/docker/.env` as `RAGFLOW_IMAGE`) |
| **Embedding model** | TEI sidecar running `BAAI/bge-small-en-v1.5` (1.2GB). Enabled via `COMPOSE_PROFILES` in RAGFlow's `.env`. No external API needed for embeddings. |
| **Dataset creation** | Must pass `embedding_model` in `model@provider` format (e.g. `BAAI/bge-small-en-v1.5@Builtin`). Without it, retrieval returns `Model(@None) not authorized`. |
| **Parse trigger endpoint** | `POST /api/v1/datasets/{dataset_id}/chunks` with `{"document_ids": [...]}`. NOT `.../documents/parse` (returns 405). |
| **Retrieval endpoint** | `POST /api/v1/retrieval` with `{"dataset_ids": [...], "question": "...", "top_k": N}`. Response: `data.chunks[]`. |
| **ES on macOS** | Elasticsearch gets OOM-killed with default settings. Fixed: `ES_JAVA_OPTS=-Xms512m -Xmx512m`, `mem_limit: 2147483648` in `docker-compose-base.yml`. |
| **Start script** | `bash scripts/start_ragflow.sh` — starts Docker, sets vm.max_map_count. |
| **Search error surfacing** | `_search_http()` now prints `[RAGFlow] search error code N: message` instead of silently returning `[]`. |

---

## Implementation Checklist

### Phase 0: Pydantic Contract Definition ✅

- [x] `ProjectDossier`, `Stakeholder`, `TechConstraint`, `CoreLogicFlow` in `contracts/project.py`.

---

### Phase 1: Ingestion Infrastructure (The RAG Pipeline) ✅

- [x] RAG Client, Librarian, RAG search tool, config, tests, demos, multi-provider support, docs.
- [x] `scripts/rag_demo.py` — end-to-end RAG: sync → parse → search returns real chunks.
- [x] `scripts/rag_agent_demo.py` — RAG → Discovery agent → Pain-Monetization Matrix.

---

### Phase 2: LiteLLM Integration & Model Tiers

*Goal: Replace the hand-rolled provider layer with LiteLLM. Get cost tracking, retries, fallbacks, and tier-based model routing for free.*

**Why LiteLLM:** The custom `providers/` layer (~400 lines, 5 files) reimplements what LiteLLM does in one function call. Phases 3–5 need cost tracking, budget caps, tier escalation, and model fallbacks — all of which LiteLLM provides out of the box. Building these ourselves would mean maintaining a bespoke LLM abstraction layer, which is not what this project is about.

#### 2.1 Add LiteLLM dependency

- [ ] Add `litellm>=1.40.0` to `requirements.txt`.
- [ ] `pip install litellm` in the venv.
- [ ] Verify: `python -c "import litellm; print(litellm.__version__)"`.

#### 2.2 Replace providers/ with a single LiteLLM provider

- [ ] Create `providers/litellm_provider.py` — a single class that wraps `litellm.completion()`:
  ```python
  class LiteLLMProvider(LLMProvider):
      def complete(self, system_prompt, user_message, model=None, max_tokens=4096):
          response = litellm.completion(
              model=model or self.default_model,
              messages=[
                  {"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_message},
              ],
              max_tokens=max_tokens,
              num_retries=3,
          )
          return LLMResponse(
              content=response.choices[0].message.content,
              input_tokens=response.usage.prompt_tokens,
              output_tokens=response.usage.completion_tokens,
              model=response.model,
              provider="litellm",
              cost=response._hidden_params.get("response_cost", 0),
          )
  ```
- [ ] Add `cost: float = 0.0` field to `LLMResponse` in `providers/base.py`.
- [ ] Update `providers/factory.py`: `get_provider()` should return `LiteLLMProvider` for all providers. Keep the function signature (`provider_name`, `model`) but map to LiteLLM model strings internally:
  ```python
  def get_provider(provider_name=None, model=None) -> LLMProvider:
      litellm_model = _to_litellm_model(provider_name, model)
      return LiteLLMProvider(default_model=litellm_model)
  ```
  Where `_to_litellm_model("gemini", "gemini-2.0-flash")` → `"gemini/gemini-2.0-flash"`, and `_to_litellm_model("openai", "gpt-4o")` → `"gpt-4o"`.
- [ ] **Do not delete** the old provider files yet. Keep them but unused — we can clean up once everything works.
- [ ] **Nothing else changes.** `BaseAgent` still calls `self.llm_provider.complete()`. The interface is identical.

#### 2.3 Set up cost tracking callback

- [ ] Create `providers/cost_logger.py` with a `CustomLogger`:
  ```python
  from litellm.integrations.custom_logger import CustomLogger

  class SwarmCostLogger(CustomLogger):
      def __init__(self):
          self.total_cost = 0.0
          self.calls = []

      def log_success_event(self, kwargs, response_obj, start_time, end_time):
          cost = kwargs.get("response_cost", 0)
          self.total_cost += cost
          meta = kwargs.get("litellm_params", {}).get("metadata", {})
          model = kwargs.get("model", "unknown")
          tier = meta.get("tier", "?")
          agent = meta.get("agent", "unknown")
          print(f"  [{agent} tier:{tier} {model}] → ${cost:.4f}")
          self.calls.append({"agent": agent, "tier": tier, "model": model, "cost": cost})
  ```
- [ ] Register it at startup (in `config.py` or wherever LiteLLM is first imported):
  ```python
  import litellm
  litellm.callbacks = [SwarmCostLogger()]
  ```
- [ ] Pass `metadata={"agent": self.role, "tier": self.tier}` in every `litellm.completion()` call from `LiteLLMProvider.complete()`. This gives us per-agent cost attribution for free.

#### 2.4 Define model tiers via LiteLLM Router

- [ ] Create `providers/router.py` that sets up a `litellm.Router` with tier aliases:
  ```python
  from litellm import Router

  def create_router() -> Router:
      return Router(model_list=[
          # Tier 1: Cheap — extraction, mining
          {"model_name": "tier1", "litellm_params": {"model": "gemini/gemini-2.0-flash"}},
          {"model_name": "tier1", "litellm_params": {"model": "gpt-4o-mini"}, "order": 2},  # fallback

          # Tier 2: Mid — critic reviews
          {"model_name": "tier2", "litellm_params": {"model": "anthropic/claude-3-5-haiku-20241022"}},
          {"model_name": "tier2", "litellm_params": {"model": "gpt-4o-mini"}, "order": 2},

          # Tier 3: Expert — synthesis, proposals
          {"model_name": "tier3", "litellm_params": {"model": "gpt-4o"}},
          {"model_name": "tier3", "litellm_params": {"model": "anthropic/claude-sonnet-4-20250514"}, "order": 2},
      ],
      num_retries=2,
      fallbacks=[{"tier1": ["tier3"]}],  # If tier1 fails hard, escalate to tier3
      enable_pre_call_checks=True,
      )
  ```
- [ ] When agent has a `tier` set, call `router.completion(model="tier1", ...)` instead of `litellm.completion(model="gemini/gemini-2.0-flash", ...)`. The Router handles retries, fallbacks, and model selection.
- [ ] Make the `model_list` configurable via `config.py` or a `model_tiers.yaml` so users can swap models without code changes.

#### 2.5 Wire tiers into agents

- [ ] Add `DEFAULT_TIER` class attribute to each agent:
  - `DiscoveryAgent` → `"tier1"`
  - `CriticAgent` → `"tier2"`
  - `ArchitectAgent`, `EstimatorAgent`, `ProposalAgent` → `"tier3"`
- [ ] In `BaseAgent.__init__`: if `tier` is set (from class default or constructor), use the Router. If explicit `model` is passed (e.g. from `--model` CLI arg), bypass the Router and call `litellm.completion()` directly with that model.

#### 2.6 Set global budget cap

- [ ] In config or at startup:
  ```python
  litellm.max_budget = settings.max_cost_per_run_usd  # e.g. 5.0
  ```
  This replaces the custom budget logic in `orchestrator/cost_controller.py`. LiteLLM raises `BudgetExceededError` automatically.
- [ ] Catch `BudgetExceededError` in `BaseSwarm.run_with_critique()` and handle gracefully (return best output so far with an escalation note).

#### 2.7 Simplify cost controller

- [ ] Refactor `orchestrator/cost_controller.py` to read from `SwarmCostLogger` instead of doing its own tracking. The cost controller becomes a thin reporting layer:
  - `total_cost_usd` → reads from the logger's `total_cost`
  - `generate_manifest()` → formats the logger's `calls` list
  - Delete all the manual token-to-cost math.

#### 2.8 Test

- [ ] `tests/test_litellm_provider.py`:
  - Mock `litellm.completion` and verify `LiteLLMProvider.complete()` returns correct `LLMResponse` with cost.
  - Verify `_to_litellm_model()` mapping for all providers.
  - Verify tier resolution via Router (mock Router).
- [ ] Run existing tests — they should still pass since `LLMProvider` interface is unchanged.

**Verification:**
```bash
# Quick (no RAGFlow needed):
python scripts/rag_agent_demo.py -p openai -m gpt-4o-mini --no-sync
# Should show per-call cost logging like: [discovery tier:1 gpt-4o-mini] → $0.0012

# With tiers (no explicit -p):
python scripts/rag_agent_demo.py --no-sync
# Should auto-select tier1 model for discovery
```

---

### Phase 3: The "Miner" Swarm (Compaction)

*Goal: Turn RAG chunks into a structured `ProjectDossier` JSON using Tier 1 models.*

- [ ] **3.1 Miner Agent.** Create `agents/miner_agent.py`:
  - `DEFAULT_TIER = "tier1"`
  - System prompt instructs the model to extract structured facts from RAG chunks.
  - Output contract: `ProjectDossier` (already defined in `contracts/project.py`).
  - **Keep the prompt tight.** Tier 1 models need explicit JSON schema in the system prompt and short, focused instructions. Don't give them essay-length prompts.

- [ ] **3.2 Ingestion Swarm.** Create `swarms/ingestion_swarm.py`:
  - Step 1: Call `rag_search()` with a set of extraction queries (pain points, tech stack, stakeholders, constraints — similar to `RAG_QUERIES` in `rag_agent_demo.py`).
  - Step 2: Feed concatenated chunks to MinerAgent → `ProjectDossier`.
  - Step 3: Validate output against Pydantic schema. If validation fails, retry once with the error message appended to the prompt.
  - Register in `swarms/__init__.py`.
  - **Do not create multiple sub-agents** (business miner, tech miner, aggregator) unless a single MinerAgent demonstrably fails. Start simple — one agent, one pass. Split later if needed.

- [ ] **3.3 Demo integration.** Add `--mode dossier` to `rag_agent_demo.py` (or a new `scripts/dossier_demo.py`) that runs: sync → ingestion swarm → writes `outputs/dossier.json`.

- [ ] **3.4 Test.** `tests/test_miner_agent.py` — mock `litellm.completion` to return a valid `ProjectDossier` JSON, verify Pydantic validation passes. Test with deliberately malformed JSON to verify retry logic.

**Verification:** `python scripts/rag_agent_demo.py --mode dossier` produces a valid `dossier.json` from the sample workspace files. Cost log should show tier1 model usage.

---

### Phase 4: Expert Synthesis (Dossier-Primed Pipeline)

*Goal: Expert (Tier 3) agents work from the Dossier, not raw content. Targeted RAG only when needed.*

- [ ] **4.1 Dossier-first input.** Modify `GreenfieldSwarm.execute()` (and Brownfield/Greyfield) to accept an optional `dossier: ProjectDossier` parameter. When provided:
  - Skip Discovery agent (the Dossier IS the discovery output, transformed).
  - Convert Dossier fields to the `PainMonetizationMatrix` contract that downstream agents expect (write a `dossier_to_pain_matrix()` adapter function in `contracts/adapters.py`).
  - Feed the adapted data to Architect → Estimator → Proposal as before.

- [ ] **4.2 JIT RAG fallback.** In expert agent system prompts, include the instruction: "If the provided context is insufficient for a specific detail, say NEED_MORE: <query>". In `BaseSwarm.run_with_critique()`, check agent output for `NEED_MORE` patterns. If found, run `rag_search(query)`, append results, and re-run the agent. Limit to 2 JIT lookups per agent to prevent loops.

- [ ] **4.3 Cost comparison.** Add a `--compare` flag to the demo that runs the same input twice: once with raw transcript (current path) and once with Dossier-primed path. Print token usage and cost side-by-side using the `SwarmCostLogger`. Target: **>50% cheaper** for the Dossier path.

- [ ] **4.4 Test.** `tests/test_dossier_pipeline.py` — mock agents, verify that when a Dossier is provided, Discovery is skipped and the adapter produces valid `PainMonetizationMatrix`.

---

### Phase 5: Quality Gate (Tiered Critic Loop)

*Goal: Cheap critics, expensive fixers. LiteLLM Router handles the escalation.*

- [ ] **5.1 Critic uses Tier 2.** `CriticAgent` already has `DEFAULT_TIER = "tier2"` from Phase 2.5 — verify it works end-to-end here.

- [ ] **5.2 Tier escalation on failure.** The Router's `fallbacks` config (`{"tier1": ["tier3"]}`) already handles automatic escalation when tier1 fails with API errors. For **quality-based** escalation (critic rejects output), modify `base_swarm.py` `run_with_critique()`:
  - Iteration 1: re-run agent at original tier with critic feedback.
  - Iteration 2+: re-run agent with `model="tier3"` (override the tier) with all accumulated feedback.
  - This is a one-line change: pass `model="tier3"` to the agent's `run()` on iteration 2+.
  - **Do not change the CriticAgent's tier** — critics always stay at Tier 2.

- [ ] **5.3 Budget warning.** Add `cost_warning_threshold: float = 0.8` to `config.py`. In the `SwarmCostLogger`, when `total_cost >= max_budget * warning_threshold`, log a warning. LiteLLM's `max_budget` handles the hard cutoff — we just add the warning.

- [ ] **5.4 End-to-end acceptance test.** Run full Greenfield pipeline with sample data:
  ```bash
  python scripts/rag_agent_demo.py --full
  ```
  Should complete without errors, produce a proposal in `outputs/`, and print a cost summary showing tier breakdown from the logger.

---

## Known Issues & Tech Debt

| Issue | Priority | Notes |
|-------|----------|-------|
| Old `providers/` files (anthropic, openai, gemini, deepseek) | Medium | Keep until Phase 2 is verified, then delete. |
| `google.generativeai` is deprecated | Resolved by LiteLLM | LiteLLM uses its own Gemini integration; we no longer call `google.generativeai` directly. |
| Python 3.9 on host | Low | RAGFlow SDK needs 3.12+ (we use HTTP fallback). Consider upgrading venv. |
| `run_factory()` passes provider/model redundantly | Low | Passed to both `EngagementManager.__init__()` and `.run()`. Harmless but confusing. |
| Tests are mock-heavy, no integration tests | Medium | 71 tests, all mocked. Consider one optional integration test per provider gated behind `--integration` flag. |
| RAGFlow SDK path (`_*_sdk` methods) is untested | Low | We only use HTTP fallback. SDK methods may have bit-rotted. |
| Manual `calculate_cost()` in `config.py` | Resolved by LiteLLM | LiteLLM tracks real costs per model. Delete `calculate_cost()`, `input_token_cost_per_million`, `output_token_cost_per_million` after Phase 2. |

---

## Instructions for Cursor / Claude Code

1. **Phase 1 is done. Start with Phase 2.**
2. **Use LiteLLM for everything LLM-related.** Cost tracking, retries, fallbacks, model routing — do not reimplement these. If you find yourself writing cost math or retry loops, stop and use LiteLLM's built-in feature instead.
3. **Keep the `LLMProvider` interface.** Agents call `self.llm_provider.complete()`. The provider is now backed by `litellm.completion()` instead of per-provider SDKs. This means `BaseAgent`, swarms, and the demo scripts don't change.
4. **Tiers are Router model aliases**, not a new abstraction layer. `"tier1"`, `"tier2"`, `"tier3"` are `model_name` values in the Router's `model_list`. An agent calls `router.completion(model="tier1", ...)` and the Router picks the actual model.
5. **Do not create unnecessary classes.** No `TierManager`, `ModelSelector`, or `CostAggregator`. LiteLLM's Router IS the tier manager. The `CustomLogger` callback IS the cost aggregator.
6. **Test each phase** before moving on. Mocked unit tests are fine. Run the demo scripts to verify end-to-end.
7. **Keep prompts short for Tier 1 models.** Gemini Flash and GPT-4o-mini need concise, structured prompts with explicit JSON schemas. They perform poorly with long, nuanced instructions.
8. **Validate the demo works after every change:** `python scripts/rag_agent_demo.py -p openai -m gpt-4o-mini --no-sync` (fast, no RAGFlow needed for LLM-only changes).
9. **Do not modify RAGFlow config or Docker files.** The RAGFlow setup is stable. If retrieval breaks, check the operational notes table above before changing anything.
10. **Model IDs matter.** Use LiteLLM model strings from the table above. The format is `provider/model-name`.

---

## Next Step

> Start with **Phase 2.1–2.2**: `pip install litellm`, create `LiteLLMProvider`, update `get_provider()` factory. Verify existing demo still works with `python scripts/rag_agent_demo.py -p openai -m gpt-4o-mini --no-sync`.
