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
| LiteLLM provider | `providers/litellm_provider.py` — wraps `litellm.completion()`, handles tier routing to Router |
| Provider factory | `providers/factory.py` — `get_provider()` returns `LiteLLMProvider` for all providers |
| Cost logger | `providers/cost_logger.py` — `SwarmCostLogger` (LiteLLM `CustomLogger` callback), singleton via `get_swarm_cost_logger()` |
| Tier router | `providers/router.py` — `get_router()` returns singleton `litellm.Router` with tier1/tier2/tier3 model aliases |
| Cost controller | `orchestrator/cost_controller.py` — thin reporting layer, reads from `SwarmCostLogger`, sets `litellm.max_budget` |
| Miner agent | `agents/miner_agent.py` — tier1, extracts `ProjectDossier` from RAG context. Also defines `MINER_RAG_QUERIES` (6 queries). |
| Ingestion swarm | `swarms/ingestion_swarm.py` — `IngestionSwarm` + `IngestionInput`. RAG retrieval → MinerAgent → Critic → `ProjectDossier`. |
| Critic agent | `agents/critic_agent.py` — hardcodes `tier: "tier2"` via `set_metadata()` (no class-level `DEFAULT_TIER`) |
| Base agent | `agents/base_agent.py` — `__init__` reads `DEFAULT_TIER` from class, sets metadata, resolves model via tier or explicit |
| Critic loop | `swarms/base_swarm.py` `run_with_critique()` — catches `BudgetExceededError`, sequential review, enriched re-run |
| Contracts | `contracts/project.py` — `ProjectDossier`, `MinerInput`, `Stakeholder`, `TechConstraint`, `CoreLogicFlow` |
| RAG client | `librarian/rag_client.py` — HTTP client for RAGFlow API |
| RAG search tool | `agents/tools/rag_search.py` — `rag_search(query, dataset_id, top_k)` |
| Config | `config.py` — pydantic-settings, `META_FACTORY_` prefix, `.env` loaded at import |
| Critic score scale | **0.0–1.0**, pass threshold `0.7` (`config.py: critic_pass_score`) |
| Demo scripts | `scripts/rag_demo.py` (RAG only), `scripts/rag_agent_demo.py` (RAG + agents, supports `--mode discovery\|dossier\|full`) |
| Legacy providers | `providers/anthropic_provider.py`, `openai_provider.py`, `gemini_provider.py` — **unused, kept for reference** |

### Agent tier assignments

| Agent | `DEFAULT_TIER` | File |
|-------|---------------|------|
| `MinerAgent` | `tier1` | `agents/miner_agent.py:51` |
| `DiscoveryAgent` | `tier1` | `agents/discovery_agent.py:81` |
| `CriticAgent` | `tier2` (via `set_metadata`) | `agents/critic_agent.py:95` |
| `ArchitectAgent` | `tier3` | `agents/architect_agent.py:116` |
| `EstimatorAgent` | `tier3` | `agents/estimator_agent.py:127` |
| `SynthesisAgent` | `tier3` | `agents/synthesis_agent.py:114` |
| `ProposalAgent` | `tier3` | `agents/proposal_agent.py:136` |

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

### How tier routing works (Phase 2, for reference)

1. Agent sets `DEFAULT_TIER = "tier1"` as class attribute.
2. `BaseAgent.__init__` reads `DEFAULT_TIER`, sets `self.model = "tier1"`, calls `self.llm_provider.set_metadata({"agent": self.role, "tier": "tier1"})`.
3. When `self.llm_provider.complete()` is called with `model="tier1"`, `LiteLLMProvider` detects the tier name and delegates to `get_router().completion(model="tier1", ...)`.
4. The Router picks the primary model for that tier (e.g. `gpt-4o-mini` for tier1) and handles retries/fallbacks.
5. If an explicit `--model` is passed via CLI, it overrides the tier and goes directly to `litellm.completion()`.

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

### Phase 2: LiteLLM Integration & Model Tiers ✅

*Replaced the hand-rolled provider layer with LiteLLM. Cost tracking, retries, fallbacks, and tier-based model routing now handled by LiteLLM.*

- [x] **2.1** `litellm>=1.40.0` added to requirements, installed, verified.
- [x] **2.2** `LiteLLMProvider` in `providers/litellm_provider.py` — wraps `litellm.completion()`, supports tier routing via Router, model alias mapping via `_to_litellm_model()`. `get_provider()` now returns `LiteLLMProvider` for all providers.
- [x] **2.3** `SwarmCostLogger` in `providers/cost_logger.py` — LiteLLM `CustomLogger` callback, tracks per-call cost with agent/tier metadata, singleton pattern, auto-registered in `litellm.callbacks`.
- [x] **2.4** Tier Router in `providers/router.py` — `litellm.Router` with tier1 (gpt-4o-mini / gemini-2.0-flash), tier2 (gpt-4o-mini / claude-haiku), tier3 (gpt-4o / claude-sonnet). Singleton via `get_router()`.
- [x] **2.5** `DEFAULT_TIER` on all agents: Discovery=tier1, Critic=tier2, Architect/Estimator/Synthesis/Proposal=tier3. `BaseAgent.__init__` reads it, sets metadata, resolves model.
- [x] **2.6** `reset_cost_controller()` sets `litellm.max_budget`. `BaseSwarm.run_with_critique()` catches `BudgetExceededError` and returns best output with escalation.
- [x] **2.7** `CostController` simplified to thin reporting layer — reads `total_cost` from `SwarmCostLogger`, `generate_manifest()` formats logger's `calls` list, no manual token-to-cost math.
- [x] **2.8** `tests/test_litellm_provider.py` — tests model mapping, provider.complete(), tier routing via Router, metadata passing, cost extraction.

**Remaining tech debt from Phase 2 (non-blocking):**
- `TokenUsage.total_cost` in `base_agent.py` still calls `settings.calculate_cost()` (legacy token math). Harmless — real cost comes from `SwarmCostLogger`. Can delete `calculate_cost()` later.
- `config.py` still has `input_token_cost_per_million` / `output_token_cost_per_million` fields. Unused by LiteLLM path. Can clean up later.
- `list_providers()` in factory.py still instantiates legacy provider classes for availability checking. Works but redundant.
- Tier model list is hardcoded in `router.py`. Not yet configurable via config. Fine for now.

---

### Phase 3: The "Miner" Swarm (Compaction) ✅

*Goal: Turn RAG chunks into a structured `ProjectDossier` JSON using Tier 1 models. The Dossier becomes the compressed, validated input for all downstream agents.*

#### 3.1 Define `MinerInput` contract

- [x] Add to `contracts/project.py`:
  ```python
  class MinerInput(BaseModel):
      """Input for the Miner Agent."""
      rag_context: str = Field(..., description="Concatenated RAG chunks, grouped by query")
      client_name: str = Field(..., description="Client or project name")
      mode: Optional[str] = Field(None, description="greenfield, brownfield, or greyfield")
  ```
- [x] Export `MinerInput` from `contracts/__init__.py`.

**Why a separate contract:** `DiscoveryInput` has `transcript` + `context` + `focus_areas`. The Miner's input is different — it's pre-structured RAG context, not a raw transcript. Keeping them separate makes the pipeline data flow explicit.

#### 3.2 Create the Miner Agent

- [x] Create `agents/miner_agent.py`. Follow the `DiscoveryAgent` pattern exactly:

```python
class MinerAgent(BaseAgent):
    DEFAULT_TIER = "tier1"
    SYSTEM_PROMPT = """..."""  # See prompt spec below

    def __init__(self, librarian=None, model=None, provider=None):
        super().__init__(
            role="miner",
            system_prompt=self.SYSTEM_PROMPT,
            output_schema=ProjectDossier,
            librarian=librarian,
            model=model,
            provider=provider,
        )

    def get_task_description(self) -> str:
        return "Extract structured project facts from RAG-retrieved context"

    def extract(self, rag_context: str, client_name: str, mode: str = None) -> ProjectDossier:
        input_data = MinerInput(rag_context=rag_context, client_name=client_name, mode=mode)
        result = self.run(input_data, max_retries=2)  # tier1 needs extra retry budget
        return result.output
```

- [x] Register in `agents/__init__.py`.

**Miner system prompt** (must be concise for tier1):

```
You are a Fact Extractor. Your job is to read RAG-retrieved context about a project
and produce a structured ProjectDossier JSON.

## Rules
1. Extract ONLY facts stated in the input. Do not invent or assume.
2. If information for a field is not present, use sensible defaults:
   - stakeholders: empty list [] if none mentioned
   - tech_stack_detected: empty list [] if none mentioned
   - constraints: empty list [] if none mentioned
   - logic_flows: empty list [] if none mentioned
   - legacy_debt_summary: null unless brownfield/greyfield mode
3. Deduplicate: if the same stakeholder/constraint/flow appears in multiple chunks, merge them.
4. For project_name: use the client_name from the input.
5. For summary: write exactly 2 paragraphs summarizing the project goals and current state.
6. For constraints, priority must be exactly one of: "Must-have", "Should-have", "Nice-to-have".
7. Respond with ONLY valid JSON. No prose, no markdown fences, no explanation.
```

**Why this prompt works for tier1:** It's under 200 words, uses numbered rules, specifies exact valid values for enums, and tells the model what to do when data is missing (instead of leaving it to hallucinate). The `BaseAgent._build_full_system_prompt()` will append the JSON schema automatically.

#### 3.3 Define RAG queries mapped to Dossier fields

- [x] Create `MINER_RAG_QUERIES` in `agents/miner_agent.py` (or a shared location):

```python
MINER_RAG_QUERIES = [
    # → stakeholders
    "Who are the key stakeholders, users, or decision-makers? What are their roles and concerns?",
    # → tech_stack_detected + constraints
    "What technologies, frameworks, programming languages, databases, or infrastructure are used or required?",
    # → constraints
    "What technical constraints, business requirements, compliance rules, or limitations apply?",
    # → logic_flows
    "What are the main business processes, workflows, or user journeys?",
    # → summary + general context
    "What is this project about? What are the goals, scope, and current status?",
    # → legacy_debt_summary (brownfield/greyfield only)
    "What technical debt, legacy systems, or migration concerns exist?",
]
```

Each query targets 1-2 specific Dossier fields. The Miner sees all results concatenated — it doesn't need to know which query produced which chunk.

**Contrast with `RAG_QUERIES` in `rag_agent_demo.py`:** Those are Discovery-oriented (pain points, success criteria). These are extraction-oriented (facts, structure, constraints). Different purpose, different queries.

#### 3.4 Create the Ingestion Swarm

- [x] Create `swarms/ingestion_swarm.py`:

```python
class IngestionInput:
    def __init__(self, client_name: str, dataset_id: str = None, mode: str = None):
        self.client_name = client_name
        self.dataset_id = dataset_id
        self.mode = mode

class IngestionSwarm(BaseSwarm):
    @property
    def mode_name(self) -> str:
        return "ingestion"

    def execute(self, input_data: IngestionInput) -> Dict[str, Any]:
        # Step 1: Retrieve RAG context
        rag_context = self._retrieve_context(input_data.dataset_id)
        if not rag_context:
            return self._finalize_run("error")  # Nothing to mine

        # Step 2: Run MinerAgent (with critic review)
        dossier = self._run_miner(rag_context, input_data)
        if self._cost_exceeded:
            return self._finalize_run("cost_exceeded")

        return self._finalize_run("completed")

    def _retrieve_context(self, dataset_id: str = None) -> str:
        """Run MINER_RAG_QUERIES against RAGFlow and concatenate results."""
        # Same pattern as build_rag_transcript() in rag_agent_demo.py
        # but using MINER_RAG_QUERIES instead of RAG_QUERIES

    def _run_miner(self, rag_context: str, input_data: IngestionInput) -> ProjectDossier:
        agent = MinerAgent(librarian=self.librarian, provider=self.provider, model=self.model)
        agent_input = MinerInput(
            rag_context=rag_context,
            client_name=input_data.client_name,
            mode=input_data.mode,
        )
        output, passed, escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="mining",
        )
        return output
```

- [x] Register `IngestionSwarm` and `IngestionInput` in `swarms/__init__.py`.

**Key decisions:**
- The swarm owns RAG retrieval (Step 1) and agent execution (Step 2). The agent itself does NOT call `rag_search()` — it receives pre-fetched context. This keeps the agent pure (input → output) and testable without RAGFlow.
- Uses `run_with_critique()` so the Critic reviews the Dossier for completeness. The Critic (tier2) checks: are fields populated? Is the summary coherent? Does the tech stack match the constraints?
- `_finalize_run()` from `BaseSwarm` handles artifact saving.

#### 3.5 Handle common Tier 1 validation failures

The `BaseAgent.run()` already retries on `json.JSONDecodeError` and `ValidationError` (up to `max_retries`). The Miner sets `max_retries=2`. Common failure modes for tier1 models:

| Failure | How the retry handles it |
|---------|-------------------------|
| JSON wrapped in markdown fences | `_parse_and_validate()` already strips ` ```json ``` ` |
| Prose before/after JSON | Already handled by fence stripping |
| `priority` not in allowed values | `ValidationError` → retry with error message showing valid values |
| Missing `project_name` or `summary` | `ValidationError` → retry with error specifying required fields |
| Empty response | `json.JSONDecodeError` → retry |

No additional error handling needed beyond what `BaseAgent` provides. The key is the prompt: by specifying exact valid values for `priority` and telling the model to use `[]` for missing lists, we prevent most failures before they happen.

#### 3.6 Demo integration

- [x] Add `--mode dossier` to `scripts/rag_agent_demo.py`:

```python
if args.mode == "dossier":
    from swarms import IngestionSwarm, IngestionInput
    swarm = IngestionSwarm(librarian=lib, run_id="dossier_demo", provider=args.provider, model=args.model)
    result = swarm.execute(IngestionInput(client_name=args.client, dataset_id=dataset_id))
    # Print the dossier from artifacts
```

This runs: RAGFlow sync → RAG retrieval (MINER_RAG_QUERIES) → MinerAgent → Critic → `outputs/dossier_demo/mining.json`.

#### 3.7 Test

- [x] Create `tests/test_miner_agent.py`:

  **Test 1: Valid extraction.** Mock `litellm.completion` to return a valid `ProjectDossier` JSON string. Verify `MinerAgent.extract()` returns a validated `ProjectDossier` with correct fields.

  **Test 2: Retry on malformed JSON.** Mock first call to return prose + partial JSON, second call to return valid JSON. Verify `result.retries == 1`.

  **Test 3: Retry on invalid priority.** Mock first call to return JSON with `priority: "High"` (wrong — should be "Must-have"), second call to return corrected JSON. Verify retry fires.

  **Test 4: Empty RAG context.** Pass `rag_context=""` — verify the Miner still produces a valid (mostly empty) Dossier rather than crashing.

  **Test 5: `_to_litellm_model` respects tier.** Verify that `MinerAgent` with no explicit model uses `DEFAULT_TIER = "tier1"`.

- [x] Create `tests/test_ingestion_swarm.py`:

  **Test 1: Full pipeline.** Mock `rag_search` to return canned chunks, mock `litellm.completion` for both Miner and Critic. Verify `execute()` returns `status: "completed"` and `artifacts["mining"]` is a valid `ProjectDossier`.

  **Test 2: Empty RAG.** Mock `rag_search` to return `[]` for all queries. Verify swarm returns gracefully (not crash).

**Verification:**
```bash
# With RAGFlow running:
python scripts/rag_agent_demo.py --mode dossier --no-sync
# Should print a ProjectDossier JSON and cost log showing tier1 usage

# Without RAGFlow (LLM-only, for testing agent/prompt):
pytest tests/test_miner_agent.py -v
```

---

### Phase 4: Expert Synthesis (Dossier-Primed Pipeline)

*Goal: Expert (Tier 3) agents work from the Dossier, not raw content. The full Forge-Stream pipeline: cheap extraction → expensive synthesis.*

#### Design decision: Dossier replaces transcript, not Discovery

The `ProjectDossier` and `PainMonetizationMatrix` serve different purposes:

| | `ProjectDossier` | `PainMonetizationMatrix` |
|---|---|---|
| **Purpose** | Factual extraction (what exists) | Analytical output (what hurts and how much) |
| **Key fields** | stakeholders, tech_stack, constraints, logic_flows | pain_points (with frequency, cost, confidence), stakeholder_needs |
| **Produced by** | Miner (tier1) | Discovery (tier1) |
| **Has monetization data?** | No | Yes (cost_per_incident, annual_cost) |

These are complementary, not redundant. The Dossier **replaces the raw transcript** as input to Discovery — making Discovery faster and cheaper because it works from structured facts instead of messy text. Discovery still does the analytical work (identify pain, monetize, prioritize).

#### 4.1 Dossier-to-transcript adapter

- [ ] Create `contracts/adapters.py`:

```python
from contracts import ProjectDossier, DiscoveryInput

def dossier_to_discovery_input(dossier: ProjectDossier) -> DiscoveryInput:
    """Format a ProjectDossier as a structured transcript for Discovery.

    Discovery expects a DiscoveryInput with a `transcript` string.
    We render the Dossier's structured fields as a readable document
    so Discovery can analyze it for pain points, monetization, etc.
    """
    sections = [f"# Project: {dossier.project_name}\n\n{dossier.summary}"]

    if dossier.stakeholders:
        lines = ["## Stakeholders"]
        for s in dossier.stakeholders:
            concerns = ", ".join(s.concerns) if s.concerns else "none stated"
            lines.append(f"- **{s.name}** ({s.role}): {concerns}")
        sections.append("\n".join(lines))

    if dossier.tech_stack_detected:
        sections.append("## Tech Stack\n" + ", ".join(dossier.tech_stack_detected))

    if dossier.constraints:
        lines = ["## Constraints"]
        for c in dossier.constraints:
            lines.append(f"- [{c.priority}] {c.category}: {c.requirement}")
        sections.append("\n".join(lines))

    if dossier.logic_flows:
        lines = ["## Core Flows"]
        for f in dossier.logic_flows:
            lines.append(f"- **Trigger:** {f.trigger} → **Process:** {f.process} → **Outcome:** {f.outcome}")
        sections.append("\n".join(lines))

    if dossier.legacy_debt_summary:
        sections.append(f"## Legacy / Tech Debt\n{dossier.legacy_debt_summary}")

    return DiscoveryInput(transcript="\n\n".join(sections))
```

**Why render as markdown, not pass raw JSON:** Discovery's system prompt is written for natural-language transcripts. A readable rendering of the Dossier matches Discovery's expected input format. If we passed raw JSON, Discovery would spend tokens parsing structure instead of analyzing content.

#### 4.2 Dossier-first entry in GreenfieldSwarm

- [ ] Add optional `dossier` parameter to `GreenfieldInput`:

```python
class GreenfieldInput:
    def __init__(self, transcript: str = "", client_name: str = "",
                 context: str = None, quality_priorities: list[str] = None,
                 dossier: ProjectDossier = None):
        self.transcript = transcript
        self.client_name = client_name
        self.context = context
        self.quality_priorities = quality_priorities
        self.dossier = dossier
```

- [ ] Modify `GreenfieldSwarm._run_discovery()`: if `input_data.dossier` is provided, use `dossier_to_discovery_input(input_data.dossier)` instead of building `DiscoveryInput` from `input_data.transcript`:

```python
def _run_discovery(self, input_data: GreenfieldInput) -> PainMonetizationMatrix:
    agent = DiscoveryAgent(librarian=self.librarian, provider=self.provider, model=self.model)

    if input_data.dossier:
        from contracts.adapters import dossier_to_discovery_input
        agent_input = dossier_to_discovery_input(input_data.dossier)
    else:
        agent_input = DiscoveryInput(transcript=input_data.transcript, context=input_data.context)

    output, passed, escalation = self.run_with_critique(
        agent=agent, input_data=agent_input, stage_name="discovery",
    )
    return output
```

**Nothing else changes.** The rest of the Greenfield pipeline (Architect → Estimator → Synthesis → Proposal) receives `PainMonetizationMatrix` regardless of whether it came from a raw transcript or a Dossier.

#### 4.3 Full Forge-Stream pipeline demo

- [ ] Add `--mode full-dossier` to `scripts/rag_agent_demo.py`:

```python
elif mode == "full-dossier":
    # Step 1: Ingestion → ProjectDossier (tier1 Miner)
    from swarms import IngestionSwarm, IngestionInput
    ingestion = IngestionSwarm(librarian=lib, run_id="forge_stream_ingestion", provider=args.provider, model=args.model)
    ingest_result = ingestion.execute(IngestionInput(client_name=args.client, dataset_id=dataset_id))
    dossier = ingest_result["artifacts"].get("mining")

    # Step 2: Dossier → full Greenfield pipeline (tier1 Discovery, tier3 rest)
    from swarms import GreenfieldSwarm, GreenfieldInput
    swarm = GreenfieldSwarm(librarian=lib, run_id="forge_stream_full", provider=args.provider, model=args.model)
    result = swarm.execute(GreenfieldInput(client_name=args.client, dossier=dossier))
```

This is the **full Forge-Stream pipeline**:
1. RAG sync → RAG retrieval (MINER_RAG_QUERIES)
2. MinerAgent (tier1) → `ProjectDossier` → Critic review
3. Dossier → DiscoveryAgent (tier1) → `PainMonetizationMatrix`
4. PainMatrix → Architect (tier3) → Estimator (tier3) → Synthesis (tier3) → Proposal (tier3)

Update the `--mode` choices to include `"full-dossier"`.

#### 4.4 Cost comparison

- [ ] Add `--compare` flag to demo that runs the same input through both pipelines:
  1. **Raw path:** RAG transcript → Discovery → Architect → ... → Proposal (current `--mode full`)
  2. **Dossier path:** RAG → Miner → Dossier → Discovery → Architect → ... → Proposal (`--mode full-dossier`)

  Print cost side-by-side from `SwarmCostLogger`. Reset logger between runs.

  Target: **>30% cheaper** for the Dossier path. The savings come from:
  - Discovery processing structured ~500-token Dossier rendering vs raw ~2000-token transcript
  - Fewer tokens = cheaper tier1 calls and smaller context for downstream tier3 agents

#### 4.5 Test

- [ ] Create `tests/test_adapters.py`:
  - `test_dossier_to_discovery_input_produces_valid_discovery_input`: Build a `ProjectDossier` with known fields, convert, verify `DiscoveryInput` has a `transcript` containing all stakeholder names, tech stack items, constraint requirements.
  - `test_empty_dossier_produces_minimal_transcript`: Dossier with empty lists → transcript still valid (just project name + summary).
  - `test_legacy_debt_included_only_when_present`: Verify `legacy_debt_summary` appears in transcript only when non-null.

- [ ] Create `tests/test_dossier_pipeline.py`:
  - Mock agents. Pass `GreenfieldInput(dossier=sample_dossier)`. Verify Discovery receives structured transcript (not raw text). Verify rest of pipeline runs normally.

---

### Phase 5: Quality Gate (Tiered Critic Loop)

*Goal: Cheap critics, expensive fixers. LiteLLM Router handles the escalation.*

- [ ] **5.1 Critic uses Tier 2.** CriticAgent already sets `tier: "tier2"` via `set_metadata()` — verify it works end-to-end by checking cost logs show tier2 model usage for critics.

- [ ] **5.2 Tier escalation on quality failure.** The Router's `fallbacks` config handles API-level failures automatically. For **quality-based** escalation (critic rejects output), modify `base_swarm.py` `run_with_critique()`:
  - Iteration 1: re-run agent at original tier with critic feedback.
  - Iteration 2+: re-run agent with `model="tier3"` (override the tier) with all accumulated feedback.
  - This is a small change in the re-run block: pass `model="tier3"` to the agent's `run()` on iteration 2+.
  - **Do not change the CriticAgent's tier** — critics always stay at Tier 2.

- [ ] **5.3 Budget warning.** Add `cost_warning_threshold: float = 0.8` to `config.py`. In `SwarmCostLogger.log_success_event()`, when `total_cost >= max_budget * warning_threshold`, print a warning. LiteLLM's `max_budget` handles the hard cutoff — we just add the warning.

- [ ] **5.4 End-to-end acceptance test.** Run full pipeline with sample data:
  ```bash
  python scripts/rag_agent_demo.py --full
  ```
  Should complete without errors, produce a proposal in `outputs/`, and print a cost summary showing tier breakdown from the logger.

---

## Known Issues & Tech Debt

| Issue | Priority | Notes |
|-------|----------|-------|
| Old `providers/` files (anthropic, openai, gemini, deepseek) | Low | Unused since Phase 2. Can delete after Phase 3 is verified. |
| `TokenUsage.total_cost` calls `settings.calculate_cost()` | Low | Legacy token math in `base_agent.py`. Harmless — real cost from `SwarmCostLogger`. Delete `calculate_cost()` and related config fields when convenient. |
| `list_providers()` uses legacy provider classes | Low | `factory.py:62-78`. Still instantiates old provider classes for availability. Could use `litellm.check_valid_key()` instead. |
| `CriticAgent` hardcodes tier in `set_metadata()` | Low | Uses `"tier2"` string instead of class-level `DEFAULT_TIER`. Works but inconsistent with other agents. |
| Python 3.9 on host | Low | RAGFlow SDK needs 3.12+ (we use HTTP fallback). Consider upgrading venv. |
| `run_factory()` passes provider/model redundantly | Low | Passed to both `EngagementManager.__init__()` and `.run()`. Harmless but confusing. |
| Tests are mock-heavy, no integration tests | Medium | Consider one optional integration test per provider gated behind `--integration` flag. |
| RAGFlow SDK path (`_*_sdk` methods) is untested | Low | We only use HTTP fallback. SDK methods may have bit-rotted. |
| Tier model list hardcoded in `router.py` | Low | Not yet configurable via config/yaml. Fine for prototyping. |

---

## Instructions for Cursor / Claude Code

1. **Phases 1–3 are done. Start with Phase 4.**
2. **Use LiteLLM for everything LLM-related.** Cost tracking, retries, fallbacks, model routing — do not reimplement these.
3. **Keep the `LLMProvider` interface.** Agents call `self.llm_provider.complete()`. The provider is backed by `litellm.completion()`.
4. **Follow existing patterns exactly.** The adapter in `contracts/adapters.py` is a pure function, not a class. `GreenfieldInput` just gets an optional `dossier` field — no new swarm class needed.
5. **The Dossier replaces the transcript, not Discovery.** The adapter renders the Dossier as readable markdown for Discovery's `transcript` field. Discovery still runs and produces `PainMonetizationMatrix`. Do not skip Discovery or try to convert Dossier directly to PainMatrix.
6. **Keep changes minimal.** Phase 4 touches: `contracts/adapters.py` (new), `swarms/greenfield.py` (small change to `_run_discovery` and `GreenfieldInput`), `scripts/rag_agent_demo.py` (add `--mode full-dossier`), and tests.
7. **Test each step** before moving on. Mocked unit tests are fine. Run the demo scripts to verify end-to-end.
8. **Validate the demo works after every change:** `python scripts/rag_agent_demo.py --mode dossier --no-sync` (existing), then `--mode full-dossier --no-sync` (new).
9. **Do not modify RAGFlow config or Docker files.** The RAGFlow setup is stable.
10. **Model IDs matter.** Use LiteLLM model strings from the table above. The format is `provider/model-name`.

---

## Next Step

> Start with **Phase 4.1**: Create `contracts/adapters.py` with `dossier_to_discovery_input()`. Test with `pytest tests/test_adapters.py`. Then modify `GreenfieldInput` and `_run_discovery()` (4.2), and add `--mode full-dossier` to the demo (4.3).
