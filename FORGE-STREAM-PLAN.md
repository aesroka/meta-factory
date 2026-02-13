# Project: Forge-Stream — Implementation Roadmap (v1.0)

Plan to build the **Autonomous Consultancy Swarm** — an AI system that ingests diverse inputs (transcripts, codebases, ideas) and produces high-fidelity software proposals using methodology-grounded agents.

Built on **RAGFlow** (RAG ingestion), **LiteLLM** (tiered model routing + cost control), and a **Hybrid Context Strategy** (RAG for targeted retrieval, full-context for comprehensive analysis on high-value engagements).

---

## Developer Intent & Guardrails

**Intent:** A production tool for estimating and planning £1M+ software engagements. Quality is the primary objective. Cost efficiency is secondary but tracked.

| Rule | Description |
|------|-------------|
| **Rule 1** | Agents interact with **structured intermediates** (Dossier, PainMatrix, etc.), not raw files. The Dossier is produced by either RAG extraction (standard) or full-context analysis (premium) or both (hybrid). |
| **Rule 2** | **Tiered model routing:** Tier 0 (Oracle) for full-context analysis, Tier 1 (Cheap) for extraction, Tier 2 (Mid) for critics, Tier 3 (Expert) for synthesis. Tier selection depends on project value and quality requirements. |
| **Rule 3** | Cost tracking, retries, fallbacks, and budget enforcement are LiteLLM's job, not ours. Do not reimplement what LiteLLM provides. |
| **Rule 4** | All cross-tier data must validate against `contracts/` Pydantic models. |
| **Rule 5** | **Scale the tool to the engagement, not the other way around.** A £50K POC needs a different output than a £1M programme. The system should always think in phased delivery (POC → MVP → V1 → Extensions) and right-size its analysis depth and output detail to the engagement value. Use `--quality premium` for high-value work, `standard` for smaller engagements. |
| **Rule 6** | **Always recommend the minimum viable first release.** Proposals must include a POC or MVP phase that delivers value within 2–6 weeks. Downstream phases are extensions, not prerequisites. The client should be able to stop after any phase and still have something useful. |

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

### Phase 4: Expert Synthesis (Dossier-Primed Pipeline) ✅

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

- [x] Create `contracts/adapters.py`:

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

- [x] Add optional `dossier` parameter to `GreenfieldInput`:

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

- [x] Modify `GreenfieldSwarm._run_discovery()`: if `input_data.dossier` is provided, use `dossier_to_discovery_input(input_data.dossier)` instead of building `DiscoveryInput` from `input_data.transcript`:

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

- [x] Add `--mode full-dossier` to `scripts/rag_agent_demo.py`:

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

- [x] Add `--compare` flag to demo that runs the same input through both pipelines:
  1. **Raw path:** RAG transcript → Discovery → Architect → ... → Proposal (current `--mode full`)
  2. **Dossier path:** RAG → Miner → Dossier → Discovery → Architect → ... → Proposal (`--mode full-dossier`)

  Print cost side-by-side from `SwarmCostLogger`. Reset logger between runs.

  Target: **>30% cheaper** for the Dossier path. The savings come from:
  - Discovery processing structured ~500-token Dossier rendering vs raw ~2000-token transcript
  - Fewer tokens = cheaper tier1 calls and smaller context for downstream tier3 agents

#### 4.5 Test

- [x] Create `tests/test_adapters.py`:
  - `test_dossier_to_discovery_input_produces_valid_discovery_input`: Build a `ProjectDossier` with known fields, convert, verify `DiscoveryInput` has a `transcript` containing all stakeholder names, tech stack items, constraint requirements.
  - `test_empty_dossier_produces_minimal_transcript`: Dossier with empty lists → transcript still valid (just project name + summary).
  - `test_legacy_debt_included_only_when_present`: Verify `legacy_debt_summary` appears in transcript only when non-null.

- [x] Create `tests/test_dossier_pipeline.py`:
  - Mock agents. Pass `GreenfieldInput(dossier=sample_dossier)`. Verify Discovery receives structured transcript (not raw text). Verify rest of pipeline runs normally.

---

### Phase 5: Quality Gate (Tiered Critic Loop) ✅

*Goal: Cheap critics, expensive fixers. When a tier1 agent fails quality review, escalate to tier3 for the retry. LiteLLM Router handles model selection; we handle the escalation logic.*

**Prerequisite understanding:** The `LiteLLMProvider.complete()` method (line 122 of `litellm_provider.py`) checks if `resolved_model` is in `("tier1", "tier2", "tier3")`. If so, it routes through the LiteLLM Router. If not, it calls `litellm.completion()` directly. So for tier routing to work, the agent's `self.model` must be set to a tier string, not a concrete model name.

#### 5.1 Fix CriticAgent tier routing (bug fix)

**The problem:** `CriticAgent` sets `tier: "tier2"` via `set_metadata()` (line 95 of `critic_agent.py`), but this only affects cost **logging** — it doesn't affect model **routing**. The actual model used is determined by `self.model`, which is set to `model or self.llm_provider.default_model` (line 93). This means critics use whatever the provider's default model is (e.g. `gpt-4o-mini`), not the tier2 model list.

Compare with `BaseAgent.__init__` (line 85 of `base_agent.py`) which does:
```python
self.model = model or getattr(self.__class__, "DEFAULT_TIER", None) or self.llm_provider.default_model
```

`BaseAgent` falls back to `DEFAULT_TIER`, so agents that set `DEFAULT_TIER = "tier1"` correctly route through the Router. `CriticAgent` doesn't inherit from `BaseAgent` and doesn't have this fallback.

- [x] **Fix:** Change line 93 of `critic_agent.py` from:
  ```python
  self.model = model or self.llm_provider.default_model
  ```
  to:
  ```python
  self.model = model or "tier2"
  ```
  This makes `self.model = "tier2"` when no explicit model is passed, so `LiteLLMProvider.complete()` routes through the Router's tier2 model list (gpt-4o-mini / claude-haiku).

- [x] **Verify:** Run `python scripts/showcase_forge_stream.py` and check cost logs. Critic calls should show `tier:tier2` **and** use an actual tier2 model (not just log the metadata).

#### 5.2 Add `model` parameter to `BaseAgent.run()`

**The problem:** `BaseAgent.run()` always uses `self.model` (set at `__init__` time). To support tier escalation (5.3), we need the ability to override the model for a single call without creating a new agent instance.

- [x] Add an optional `model` parameter to `BaseAgent.run()`:

```python
def run(self, input_data: BaseModel, max_retries: int = 1, model: Optional[str] = None) -> AgentResult:
```

In the `complete()` call (line 184 of `base_agent.py`), change:
```python
model=self.model,
```
to:
```python
model=model or self.model,
```

This is backward-compatible — all existing callers don't pass `model` and get the same behavior as before.

#### 5.3 Tier escalation on quality failure

**The mechanism:** When a critic rejects an agent's output, the swarm re-runs the agent with feedback. Currently, all retries use the same tier. We want: first retry at original tier, second+ retry at tier3.

- [x] Modify `run_with_critique()` in `base_swarm.py`. In the re-run block (around line 161-169), pass `model="tier3"` to the agent's `run()` on iteration 2+:

```python
if iteration < settings.max_critic_iterations - 1:
    if rerun_fn:
        current_output = rerun_fn(current_output, verdict.objections)
    else:
        enriched_input = self._enrich_with_feedback(input_data, verdict)
        # Escalate to tier3 on second+ retry
        escalation_model = "tier3" if iteration >= 1 else None
        result = agent.run(enriched_input, model=escalation_model)
        self._update_token_usage(agent)
        current_output = result.output
```

**Why iteration >= 1 (not >= 2):** The loop is 0-indexed. `iteration=0` is the first critic review. If it fails, `iteration=0` triggers the first re-run (at original tier). If that fails too, `iteration=1` triggers the second re-run (escalated to tier3).

- [x] **Do not change the CriticAgent's tier.** Critics always stay at tier2. Only the producing agent escalates.

- [x] Update the metadata on escalation so cost logs reflect the tier override. Before the escalated `run()` call, update the agent's metadata:
  ```python
  if escalation_model and hasattr(agent, 'llm_provider') and hasattr(agent.llm_provider, 'set_metadata'):
      agent.llm_provider.set_metadata({"tier": "tier3", "escalated": True})
  ```

#### 5.4 Budget warning

- [x] Add `cost_warning_threshold: float = 0.8` to `config.py` (in the "Cost controls" section, after `max_cost_per_run_usd`).

- [x] In `SwarmCostLogger.log_success_event()` (in `providers/cost_logger.py`), after updating `self.total_cost`, add a warning check:

```python
import litellm
max_budget = getattr(litellm, 'max_budget', None)
if max_budget and self.total_cost >= max_budget * 0.8:
    remaining = max_budget - self.total_cost
    print(f"  ⚠ BUDGET WARNING: ${self.total_cost:.4f} of ${max_budget:.2f} used ({self.total_cost/max_budget*100:.0f}%). ${remaining:.4f} remaining.")
```

Read `cost_warning_threshold` from `config.py` instead of hardcoding `0.8` if you prefer, but the cost logger currently doesn't import config — hardcoding is simpler and avoids circular imports.

#### 5.5 Test

- [x] Create `tests/test_quality_gate.py`:

  **Test 1: Critic routes through tier2.** Instantiate `CriticAgent(reviewing_agent_role="discovery")` with no explicit model. Assert `agent.model == "tier2"`. Mock `litellm.completion` and verify the model passed to the Router is `"tier2"`.

  **Test 2: Tier escalation on second retry.** Mock critic to reject on first two reviews, pass on third. Mock `agent.run()` and verify: first re-run called with `model=None` (original tier), second re-run called with `model="tier3"`.

  **Test 3: Budget warning fires.** Set `litellm.max_budget = 1.0`. Create a `SwarmCostLogger`, manually call `log_success_event()` with cumulative cost = $0.85. Capture stdout and verify the warning message appears.

  **Test 4: No escalation when critic passes first time.** Mock critic to pass immediately. Verify agent `run()` is called exactly once with no model override.

#### 5.6 End-to-end verification

```bash
# Without RAGFlow (curated dossier, exercises full pipeline including critics):
python scripts/showcase_forge_stream.py -p openai

# With RAGFlow (full Forge-Stream):
python scripts/rag_agent_demo.py --mode full-dossier --no-sync
```

Check the cost logs for:
- Discovery/Miner calls: `tier:tier1`
- Critic calls: `tier:tier2` (and actual tier2 model, not default)
- Architect/Estimator/Synthesis/Proposal calls: `tier:tier3`
- If any agent was escalated: `tier:tier3, escalated:True` in the log

---

## Architecture Decision: RAG vs Context Stuffing vs Hybrid

*This section records the honest trade-off analysis. Read before implementing Phase 6.*

### The question

Modern models have massive context windows: Gemini 2.5 Pro (1M+ tokens), Claude Opus (200K tokens). An entire codebase + all project documents + the methodology "Bibles" can fit in a single call. So why use RAG at all? Why not just load everything and let the model figure it out?

### Option A: RAG-only (current approach, Phases 1–4)

**How it works:** RAGFlow chunks and embeds all documents. For each query, retrieve the top-K relevant chunks. The Miner (tier1) extracts structured facts from retrieved chunks into a ProjectDossier. Downstream agents work from the Dossier, never seeing raw documents.

| Pros | Cons |
|------|------|
| Cost-efficient — only processes relevant chunks | **Retrieval noise** — if RAG misses something, the entire pipeline misses it |
| Works with any model size (even 8K context) | **Chunking artifacts** — splits documents at arbitrary boundaries, breaking logical continuity |
| Fast — small context = fast inference | **"Lost in Retrieval"** — a single mention of "GDPR" in a 50-page doc might not surface for a tech-stack query |
| Good for development/testing | Multiple hops (RAG → Miner → Dossier → Discovery → ...) = multiple points of information loss |
| The Dossier compression is genuinely useful | For £1M+ projects, the cost savings are irrelevant compared to the risk of missing a critical requirement |

### Option B: Full-context stuffing

**How it works:** Concatenate all source documents and methodology books. Load everything into a single massive context call (Gemini 2.5 Pro or Claude Opus). The model sees the complete picture in one pass.

| Pros | Cons |
|------|------|
| **No retrieval noise** — the model sees EVERYTHING | Expensive per call (~$5-20 for a 500K token context) |
| **No chunking artifacts** — full document continuity preserved | "Lost in the Middle" syndrome — models lose attention in long contexts |
| Simpler architecture — no RAGFlow, no embedding model | Latency — a 1M token call takes 30-120 seconds |
| The model can connect dots across distant parts of documents that RAG would never surface together | Can't handle truly massive inputs (10M+ tokens) |
| For £1M+ projects, $20 per call is noise | Not all models handle long contexts equally well |

### Option C: Hybrid (recommended for v1.0)

**How it works:** Run BOTH approaches. Compare and reconcile.

1. **Full-context pass (tier0 "Oracle"):** Load all documents into a single massive call. The model sees the complete picture. Produces a comprehensive ProjectDossier. This is the "senior partner" reading everything.

2. **RAG-targeted pass (tier1):** Run the existing Miner pipeline. RAG retrieval with focused queries. Catches details that structured queries surface well.

3. **Reconciliation:** Compare the two Dossiers. Where they agree → high confidence. Where they disagree → flag for review. Produce a merged "Gold Standard" Dossier.

| Pros | Cons |
|------|------|
| Best of both worlds — comprehensive + focused | More complex architecture |
| Disagreements between approaches are a quality signal | ~2x the cost of either approach alone |
| Full-context catches what RAG misses; RAG catches what gets "lost in the middle" | Reconciliation step needs careful design |
| Appropriate for £1M+ project stakes | Overkill for small/prototype engagements |

### The honest opinion

**The right answer depends on the engagement.** RAG-only is fine for a quick £50K POC estimate — fast, cheap, good enough. But for a £500K+ programme where a missed requirement costs six figures in rework, you want the hybrid approach.

The system should offer both and let the user choose:
- `--quality standard` → RAG-only, single estimator, fast. Good for exploratory/small engagements. ~$1-5 per run.
- `--quality premium` → Hybrid context, ensemble estimation, full Bibles. Good for high-value engagements. ~$30-50 per run.

**The good news:** The architecture supports this cleanly. The Dossier is already the universal intermediate — we just need to add another way to produce it (full-context) alongside the existing way (RAG). The `MinerAgent` prompt and `ProjectDossier` schema don't change. Only the input source and analysis depth change.

### Implementation strategy (Phase 6)

Add a `context_mode` parameter: `"rag"` (default, current behavior), `"full"` (full-context only), `"hybrid"` (both + reconcile).

Add `tier0` to the Router — maps to Gemini 2.5 Pro (1M context) or Claude Opus. Used exclusively for full-context analysis.

The `IngestionSwarm` gains a `_full_context_extract()` method alongside the existing `_retrieve_context()`. In hybrid mode, it runs both and reconciles.

### What about the Bibles?

Currently, agents load **cheat sheets** (condensed summaries) from the Librarian. For tier0/tier3 agents with large context windows, loading **full Bible texts** would improve reasoning quality.

The Librarian already has two paths: `cheat_sheets/` and `library/` (full texts). Currently only cheat sheets are used. Phase 6 adds a `depth` parameter: `"cheat_sheet"` (default for tier1/tier2) vs `"full"` (for tier0/tier3 on premium engagements).

---

### Phase 6: Hybrid Context Strategy ✅

*Goal: For high-value engagements, produce the best possible ProjectDossier by running both full-context and RAG extraction, then reconciling. Add a "premium" quality tier that sacrifices cost for comprehensiveness.*

#### 6.1 Add Tier 0 ("Oracle") to the Router

- [x] Add tier0 entries to `providers/router.py`:

```python
# Tier 0: Oracle — full-context analysis (massive context windows)
{"model_name": "tier0", "litellm_params": {"model": "gemini/gemini-2.5-pro"}},
{"model_name": "tier0", "litellm_params": {"model": "anthropic/claude-opus-4-20250514"}, "order": 2},
```

- [ ] Update `LiteLLMProvider.complete()` to recognise `"tier0"` as a tier name (currently only checks `("tier1", "tier2", "tier3")`).

- [ ] Update the tier table in the Codebase Notes section of this plan.

#### 6.2 Add `context_mode` to IngestionSwarm

- [ ] Add `context_mode: str = "rag"` parameter to `IngestionInput`:

```python
class IngestionInput:
    def __init__(self, client_name: str, dataset_id: str = None,
                 mode: str = None, context_mode: str = "rag",
                 raw_documents: str = None):
        # ...
        self.context_mode = context_mode  # "rag", "full", or "hybrid"
        self.raw_documents = raw_documents  # concatenated raw text for full-context mode
```

- [ ] Add `_full_context_extract()` to `IngestionSwarm`:

```python
def _full_context_extract(self, raw_documents: str, input_data: IngestionInput) -> ProjectDossier:
    """Run MinerAgent with full document context using tier0 model."""
    agent = MinerAgent(librarian=self.librarian, model="tier0")
    # The Miner prompt stays the same — only the input size changes
    return agent.extract(rag_context=raw_documents, client_name=input_data.client_name, mode=input_data.mode)
```

- [ ] Modify `IngestionSwarm.execute()` to support all three modes:

```python
if input_data.context_mode == "rag":
    dossier = self._run_rag_pipeline(input_data)
elif input_data.context_mode == "full":
    dossier = self._full_context_extract(input_data.raw_documents, input_data)
elif input_data.context_mode == "hybrid":
    rag_dossier = self._run_rag_pipeline(input_data)
    full_dossier = self._full_context_extract(input_data.raw_documents, input_data)
    dossier = self._reconcile_dossiers(rag_dossier, full_dossier, input_data)
```

#### 6.3 Dossier Reconciliation

- [ ] Create `contracts/reconciliation.py` (or add to `adapters.py`):

```python
class DossierReconciliation(BaseModel):
    """Result of comparing RAG-extracted and full-context Dossiers."""
    merged_dossier: ProjectDossier
    agreements: List[str] = Field(default_factory=list, description="Fields where both sources agree")
    disagreements: List[str] = Field(default_factory=list, description="Fields where sources differ — flagged for review")
    rag_only_items: List[str] = Field(default_factory=list, description="Items found only via RAG")
    full_context_only_items: List[str] = Field(default_factory=list, description="Items found only via full-context")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Overall confidence in the merged dossier")
```

- [ ] Add `_reconcile_dossiers()` to `IngestionSwarm`. This is an LLM call (tier2) that takes both Dossiers as input and produces the merged result. The reconciler specifically looks for:
  - Stakeholders mentioned in one but not the other
  - Constraints that appear in full-context but were missed by RAG chunking
  - Tech stack items that RAG surfaced from code samples but full-context missed in prose
  - Logic flows described differently between the two

- [ ] Save both individual Dossiers as artifacts alongside the merged one, so the user can audit what each approach found.

#### 6.4 Librarian depth parameter

- [ ] Add `depth: str = "cheat_sheet"` parameter to `Librarian.get_context_for_agent()`:
  - `"cheat_sheet"` (default): loads from `cheat_sheets/` (current behaviour)
  - `"full"`: loads from `library/` (full Bible texts)

- [ ] In `BaseAgent.__init__`, set depth based on tier: if `DEFAULT_TIER` is `"tier0"` or `"tier3"`, use `"full"`. Otherwise use `"cheat_sheet"`. Allow override via constructor parameter.

- [ ] Verify the full Bible texts exist in `library/`. If any are missing, document which ones need to be added (the cheat sheets were condensed from these — the originals may or may not be in the repo).

#### 6.5 CLI integration

- [ ] Add `--context-mode rag|full|hybrid` to `scripts/rag_agent_demo.py` and `scripts/showcase_forge_stream.py`.

- [ ] Add `--quality standard|premium` shortcut:
  - `standard` = `context_mode="rag"`, existing tier assignments
  - `premium` = `context_mode="hybrid"`, Miner uses tier0, full Bible texts for tier3 agents

- [ ] For `main.py`, add `--quality` flag. Premium mode automatically selects hybrid context and higher-tier models.

#### 6.6 Test

- [ ] `tests/test_hybrid_context.py`:
  - **Test 1:** Full-context extraction produces valid ProjectDossier from concatenated raw text.
  - **Test 2:** Hybrid mode runs both pipelines and produces a DossierReconciliation with merged result.
  - **Test 3:** Disagreements are correctly identified (mock RAG to miss a stakeholder, verify it appears in `full_context_only_items`).
  - **Test 4:** `context_mode="rag"` still works exactly as before (backward compatibility).

**Verification:**
```bash
# Standard (RAG only, as before):
python scripts/rag_agent_demo.py --mode dossier --no-sync

# Premium (full-context, needs raw documents):
python scripts/showcase_forge_stream.py --quality premium

# Hybrid (both + reconcile):
python scripts/rag_agent_demo.py --mode dossier --context-mode hybrid --no-sync
```

---

### Phase 7: Ensemble Estimation (Wideband Delphi)

*Goal: Replace the single EstimatorAgent with the Optimist/Pessimist/Realist ensemble from the original deep research. Programmatic PERT aggregation — not LLM — combines the three independent estimates.*

**Why this matters:** A single LLM estimating a £1M project will be systematically optimistic (training data skew). Three independent perspectives with different biases, aggregated mathematically, produce statistically more reliable estimates. This is the "Outside View" from Kahneman/Flyvbjerg.

**What already exists:** The `EstimatorAgent` already has excellent PERT/McConnell prompts. The `PERTEstimate` contract has `model_validator` that checks the math. The `EstimationResult` aggregates with `sqrt(sum of variances)`. All of this stays. We split the agent into three variants with different system prompt biases.

#### 7.1 Create estimation sub-agents

- [ ] Create `agents/estimation_ensemble.py` with three subclasses:

```python
class OptimistEstimator(EstimatorAgent):
    """Assumes best-case: experienced team, clean code, no surprises."""
    BIAS_PROMPT = """
    ## Estimation Bias: OPTIMISTIC
    You are estimating the BEST REALISTIC CASE. Assume:
    - The team is experienced with the tech stack
    - Code quality is good, technical debt is manageable
    - Integration points work as documented
    - No major requirement changes mid-project
    Still use PERT, but your 'likely' estimate should lean toward 'optimistic'.
    """

class PessimistEstimator(EstimatorAgent):
    """Assumes worst-case: legacy blocks, scope creep, integration failures."""
    BIAS_PROMPT = """
    ## Estimation Bias: PESSIMISTIC
    You are estimating the WORST REALISTIC CASE. Assume:
    - Legacy code is worse than described (Feathers: 'code without tests')
    - Integration points have undocumented quirks
    - Requirements will change at least once
    - The team will encounter at least one major technical block
    Still use PERT, but your 'likely' estimate should lean toward 'pessimistic'.
    """

class RealistEstimator(EstimatorAgent):
    """Applies reference class forecasting — what ACTUALLY happens on similar projects."""
    BIAS_PROMPT = """
    ## Estimation Bias: REALIST (Reference Class Forecasting)
    You are estimating based on WHAT ACTUALLY HAPPENS, not what should happen.
    - Use the Outside View (Kahneman): how long do projects like this ACTUALLY take?
    - Apply the Planning Fallacy correction: add 30-50% to your initial gut estimate
    - If legacy systems are involved, multiply integration estimates by 1.5x
    Use PERT as normal, but anchor your 'likely' estimate to historical reality, not the plan.
    """
```

Each subclass prepends its `BIAS_PROMPT` to the base `SYSTEM_PROMPT`. The `DEFAULT_TIER`, output schema, and PERT validation all stay identical.

#### 7.2 Programmatic PERT aggregation

- [ ] Create `agents/estimation_aggregator.py` — a **pure Python function**, not an LLM call:

```python
def aggregate_ensemble(
    optimist: EstimationResult,
    pessimist: EstimationResult,
    realist: EstimationResult,
) -> EstimationResult:
    """Aggregate three independent estimates using PERT formula.

    For each task that appears in all three estimates:
    E = (Optimist + 4*Realist + Pessimist) / 6
    SD = (Pessimist - Optimist) / 6

    This is the Wideband Delphi pattern from the deep research.
    """
```

The aggregator:
1. Matches tasks across the three estimates by name/description (fuzzy match)
2. For matched tasks: applies PERT formula across the three Expected values
3. For unmatched tasks (only one estimator identified them): includes them with a warning
4. Recomputes `total_expected_hours`, `total_std_dev`, `confidence_interval_90`
5. Adds a caveat noting which tasks had disagreement

#### 7.3 Wire into swarms

- [ ] Modify `GreenfieldSwarm._run_estimation()`:

```python
def _run_estimation(self, architecture, ensemble: bool = True):
    if ensemble:
        from agents.estimation_ensemble import OptimistEstimator, PessimistEstimator, RealistEstimator
        from agents.estimation_aggregator import aggregate_ensemble

        opt_result = self._run_single_estimate(OptimistEstimator, architecture)
        pess_result = self._run_single_estimate(PessimistEstimator, architecture)
        real_result = self._run_single_estimate(RealistEstimator, architecture)

        self.run.artifacts["estimate_optimist"] = opt_result
        self.run.artifacts["estimate_pessimist"] = pess_result
        self.run.artifacts["estimate_realist"] = real_result

        return aggregate_ensemble(opt_result, pess_result, real_result)
    else:
        # Single-agent fallback (cheaper, less reliable)
        return self._run_single_estimate(EstimatorAgent, architecture)
```

- [ ] The three estimation calls can run **in parallel** (they're independent). Use `ThreadPoolExecutor` like `GreyfieldSwarm._run_parallel_analysis()` already does.

- [ ] Apply the same pattern to `BrownfieldSwarm._run_estimation()` and `GreyfieldSwarm._run_estimation()`.

- [ ] Add `--ensemble / --no-ensemble` flag to demo scripts. Default: `--ensemble` for `--quality premium`, `--no-ensemble` for standard.

#### 7.4 Test

- [ ] `tests/test_estimation_ensemble.py`:
  - **Test 1:** Each sub-agent produces valid `EstimationResult` (mock LLM, verify PERT math validates).
  - **Test 2:** Aggregator correctly applies PERT across three results for matched tasks.
  - **Test 3:** Aggregator handles unmatched tasks (task only in pessimist estimate → included with warning).
  - **Test 4:** Aggregated result passes `EstimationResult.validate_totals()`.
  - **Test 5:** Parallel execution completes without race conditions.

**Verification:**
```bash
python scripts/showcase_forge_stream.py -p openai --quality premium
# Should show 3 estimation runs + aggregated result in cost logs
```

---

### Phase 8: All Paths with Dossier Integration

*Goal: Exercise Brownfield and Greyfield swarms with the Forge-Stream infrastructure (Dossier, tier routing, hybrid context). After this phase, all three swarm types work end-to-end with the full quality pipeline.*

**What already exists:** `BrownfieldSwarm` and `GreyfieldSwarm` are fully implemented with all stages (Legacy → Architect → Estimator → Synthesis → Proposal for Brownfield; parallel Discovery + Legacy → merge → Architect → ... for Greyfield). They just haven't been wired up with the Dossier entry point, tier routing, or the context strategy from Phases 4–6.

#### 8.1 Brownfield Dossier integration

- [ ] Add optional `dossier` parameter to `BrownfieldInput`:

```python
class BrownfieldInput:
    def __init__(self, codebase_description: str = "", client_name: str = "",
                 code_samples: str = None, known_issues: list[str] = None,
                 change_requirements: str = None, dossier: ProjectDossier = None):
        # ...
        self.dossier = dossier
```

- [ ] Create `dossier_to_legacy_input()` adapter in `contracts/adapters.py`:
  - Renders the Dossier's `tech_stack_detected`, `constraints`, `logic_flows`, and `legacy_debt_summary` as a structured codebase description for the Legacy Agent.

- [ ] Modify `BrownfieldSwarm._run_legacy_analysis()`: if `input_data.dossier` is provided, use the adapter instead of raw `codebase_description`.

#### 8.2 Greyfield Dossier integration

- [ ] Add optional `dossier` parameter to `GreyfieldInput`.

- [ ] When dossier is provided:
  - Discovery gets `dossier_to_discovery_input(dossier)` (adapter from Phase 4)
  - Legacy analysis gets `dossier_to_legacy_input(dossier)` (new adapter from 8.1)
  - Both paths benefit from structured input instead of raw text

#### 8.3 IngestionSwarm mode awareness

- [ ] The `IngestionSwarm` currently runs `MINER_RAG_QUERIES` which are generic. For Brownfield, the queries should emphasize tech debt, legacy constraints, and code structure. For Greyfield, both sets.

- [ ] Add `BROWNFIELD_RAG_QUERIES` and use them when `IngestionInput.mode == "brownfield"`:

```python
BROWNFIELD_RAG_QUERIES = [
    "What legacy systems, frameworks, or languages are in use? What versions?",
    "What technical debt, code quality issues, or maintenance burdens exist?",
    "What are the integration points with other systems? What protocols and APIs?",
    "What testing coverage exists? What is untested?",
    "What deployment and infrastructure constraints apply?",
    "What business processes depend on this system? What breaks if it's down?",
]
```

#### 8.4 Demo scripts for all modes

- [ ] Add `--mode brownfield` and `--mode greyfield` to `scripts/rag_agent_demo.py`.

- [ ] Create a `scripts/showcase_brownfield.py` (curated Dossier from a legacy scenario, like `showcase_forge_stream.py` does for Greenfield).

- [ ] Verify `main.py` (which already has all modes) works end-to-end with the new Dossier integration.

#### 8.5 Test

- [ ] `tests/test_brownfield_dossier.py`: Mock agents. Verify `BrownfieldInput(dossier=X)` uses the adapter. Verify Legacy Agent receives structured input.

- [ ] `tests/test_greyfield_dossier.py`: Mock agents. Verify parallel execution still works with Dossier inputs.

**Verification:**
```bash
# Brownfield with curated dossier:
python scripts/showcase_brownfield.py --dry-run

# Greyfield via main CLI:
python main.py --input ./workspace/sample_transcript.txt --codebase ./workspace/ --client "Acme" --mode greyfield
```

---

### Phase 9: Phased Delivery Output & CLI Polish

*Goal: The system produces right-sized, phased proposals (POC → MVP → V1) for any engagement from £50K to £5M. One command, any input, structured output with incremental releases.*

**The problem with the current output:** The `ProposalDocument` has `milestones` (flat list) and `timeline_weeks` (single number). There's no concept of "stop after Phase 1 and you still have something useful." Every proposal looks like a monolithic big-bang delivery. A £50K engagement doesn't need a 30-milestone plan — it needs a 4-week POC with clear success criteria and an optional follow-on.

**What already exists:** `main.py` is already a Rich CLI with `--input`, `--client`, `--mode auto|greenfield|brownfield|greyfield`, `--classify-only`, `--list-providers`, progress spinner, and cost summaries. `InputClassifier` already does heuristic + LLM classification. This phase wires in the new features AND fundamentally changes how the output is structured.

#### 9.1 Add `DeliveryPhase` to proposal contracts

- [ ] Add to `contracts/proposal_contracts.py`:

```python
class DeliveryPhase(BaseModel):
    """A distinct release phase with its own value proposition."""
    phase_name: str = Field(..., description="e.g. 'POC', 'MVP', 'V1', 'V1.1 – Analytics Extension'")
    phase_type: str = Field(..., description="poc, mvp, v1, extension")
    goal: str = Field(..., description="What this phase proves or delivers — one sentence")
    success_criteria: List[str] = Field(..., min_length=1, description="How we know this phase is done")
    milestones: List[Milestone] = Field(..., min_length=1)
    estimated_hours: float = Field(..., ge=0, description="PERT expected hours for this phase")
    estimated_weeks: int = Field(..., ge=1)
    estimated_cost_gbp: Optional[float] = Field(None, description="Cost at the given hourly rate")
    can_stop_here: bool = Field(..., description="True if the client gets standalone value from just this phase")
    prerequisites: List[str] = Field(default_factory=list, description="Which prior phases must complete first")
```

- [ ] Update `ProposalDocument` to include phased delivery:

```python
class ProposalDocument(BaseModel):
    # ... existing fields ...
    delivery_phases: List[DeliveryPhase] = Field(..., min_length=1,
        description="Phased delivery plan: POC → MVP → V1 → Extensions. Each phase delivers standalone value.")
    recommended_first_phase: str = Field(...,
        description="Which phase to start with — usually POC or MVP")
    total_estimated_hours: float = Field(..., ge=0)
    total_estimated_weeks: int = Field(..., ge=1)
```

Keep the existing `milestones` field for backward compatibility but deprecate it in favour of `delivery_phases[*].milestones`.

#### 9.2 Update Synthesis and Proposal agent prompts

- [ ] Add to `SynthesisAgent.SYSTEM_PROMPT`:

```
## Phased Delivery Planning

ALWAYS structure the engagement as incremental phases:

1. **POC (Proof of Concept)**: 2-4 weeks. Validate the riskiest assumption.
   The client should be able to stop here if the concept doesn't work.
   
2. **MVP (Minimum Viable Product)**: 4-8 weeks after POC. Deliver the minimum
   set of features that provides real value. This is NOT a prototype — it's 
   production-ready but feature-limited.
   
3. **V1 (Full Release)**: Complete the remaining features, harden for scale.
   Only include what's needed for launch — not every nice-to-have.
   
4. **Extensions** (optional): Analytics, integrations, optimizations.
   Each extension should be independently valuable.

RULES:
- The first phase must be achievable in ≤6 weeks
- Every phase must deliver standalone value (can_stop_here=True for most)
- Each phase has explicit success criteria
- Do NOT front-load all the work into Phase 1
- A £50K engagement might only need POC + MVP. A £500K engagement needs all phases.
```

- [ ] Add to `ProposalAgent.SYSTEM_PROMPT`:

```
## Phased Investment Structure

Present the investment as a phased commitment, not a single lump sum:

"We recommend starting with a 4-week POC (£30K) to validate [riskiest assumption].
If the POC succeeds, the MVP follows (£80K, 8 weeks) delivering [core capability].
Full V1 brings [remaining scope] at £150K over 12 weeks."

The client should feel they can commit to Phase 1 without committing to the total.
Each phase's investment_summary should include hours, weeks, and cost at the given rate.
```

#### 9.3 Add quality, context, and budget flags

- [ ] Add `--quality standard|premium` to `main.py`:
  - `standard`: `context_mode="rag"`, single estimator, cheat-sheet Bibles, tier1/tier3 routing. Cost: ~$1-5 per run.
  - `premium`: `context_mode="hybrid"`, ensemble estimation, full Bible texts, tier0/tier3 routing. Cost: ~$30-50 per run.

- [ ] Add `--hourly-rate` flag (default: 150, in GBP). Used by the Proposal agent to calculate `estimated_cost_gbp` per phase.

- [ ] Add `--context-mode rag|full|hybrid` as an advanced override.

- [ ] Add `--ensemble / --no-ensemble` as an advanced override.

#### 9.4 Wire Forge-Stream pipeline into main.py

- [ ] When `--quality premium` or `--context-mode full|hybrid`:
  1. Run IngestionSwarm first to produce the Dossier
  2. Pass the Dossier to the appropriate swarm (Greenfield/Brownfield/Greyfield)
  3. This is the same flow as `--mode full-dossier` in `rag_agent_demo.py`, but integrated into the main CLI

- [ ] For standard quality, the current flow (raw content → swarm) continues to work.

#### 9.5 Progress reporting

- [ ] Replace the single `Progress` spinner with stage-by-stage reporting:

```
[1/6] Ingestion (Miner → Dossier)          ✓ $0.02, 3s
[2/6] Discovery (Pain-Monetization Matrix)  ✓ $0.08, 12s
[3/6] Architecture (Trade-off Matrix)       ✓ $0.15, 18s
[4/6] Estimation (3x Ensemble → PERT)       ✓ $0.45, 25s
[5/6] Synthesis (Engagement Summary)        ✓ $0.12, 10s
[6/6] Proposal (SCQA → Final Document)      ✓ $0.18, 15s

Total: $1.00 | 83s | 6 stages | 2 escalations
```

This requires the swarms to emit stage callbacks. Add an optional `on_stage_complete` callback to `BaseSwarm`.

#### 9.6 Output formatting

- [ ] After pipeline completion, print a structured summary:

```
═══════════════════════════════════════════════════
  Acme Logistics – Field App Modernization
═══════════════════════════════════════════════════

  Recommended: Start with POC (4 weeks, £30K)

  Phase 1: POC – Live manifest proof-of-concept
    4 weeks | 160 hrs (120–210 range) | £24,000
    Goal: Validate real-time manifest updates work with legacy routing service
    Success: Driver sees live manifest update within 5s of dispatch change

  Phase 2: MVP – Core field app
    8 weeks | 480 hrs (380–620 range) | £72,000
    Goal: Replace paper manifests for 1 depot pilot
    
  Phase 3: V1 – Full rollout
    12 weeks | 720 hrs (600–900 range) | £108,000
    Goal: All depots, offline support, audit trail

  Total (all phases): 24 weeks | 1,360 hrs | £204,000
  90% confidence interval: £156,000 – £259,500
  
  3 key risks | 1 escalation (see outputs/)
═══════════════════════════════════════════════════
```

- [ ] Save a `summary.md` alongside the JSON artifacts — a human-readable report with the phased plan that can be shared directly with clients.

- [ ] Save `proposal.md` using the existing `ProposalDocument.to_markdown()` (update it to include the phased delivery structure).

#### 9.7 Test

- [ ] `tests/test_phased_delivery.py`:
  - **Test 1:** `DeliveryPhase` contract validates correctly. POC phase with `can_stop_here=True`.
  - **Test 2:** `ProposalDocument` with `delivery_phases` validates. First phase estimated ≤6 weeks.
  - **Test 3:** Mock a full pipeline run. Verify the proposal contains at least 2 phases (POC + something).

- [ ] `tests/test_cli.py`: Use Click's `CliRunner` to test the main CLI:
  - `--classify-only` with a transcript → returns GREENFIELD
  - `--quality premium --input transcript.txt` → runs full pipeline
  - `--list-providers` → prints provider status
  - `--hourly-rate 200` → affects cost calculations in output

**Verification:**
```bash
# Small engagement (standard quality, quick):
python main.py --input ./workspace/sample_transcript.txt --client "Acme Logistics" --quality standard --hourly-rate 150

# Large engagement (premium quality, thorough):
python main.py --input ./workspace/sample_transcript.txt --client "Acme Logistics" --quality premium --hourly-rate 200

# Both should produce phased delivery plans — but the premium one will have
# more detailed estimates, hybrid-validated Dossier, and ensemble estimation.
```

---

### Phase 10: Production Hardening (v1.0 Launch)

*Goal: The system is reliable enough to use on real client engagements from £50K to £5M+. Clean up tech debt, add safety nets, document everything.*

#### 10.1 Delete dead code

- [ ] Delete legacy provider files: `providers/anthropic_provider.py`, `openai_provider.py`, `gemini_provider.py`, `deepseek_provider.py`.
- [ ] Delete `settings.calculate_cost()`, `input_token_cost_per_million`, `output_token_cost_per_million` from `config.py`.
- [ ] Clean up `list_providers()` in `factory.py` — use LiteLLM's key checking instead of legacy provider instantiation.
- [ ] Remove any commented-out code or placeholder methods.

#### 10.2 Error handling

- [ ] Add retry logic for RAGFlow API failures (network timeouts, 503s).
- [ ] Add graceful degradation: if RAGFlow is down and `context_mode="hybrid"`, fall back to `"full"` with a warning (not crash).
- [ ] Add timeout for individual LLM calls (currently `api_timeout_seconds` in config, verify it's enforced).
- [ ] Catch and report `ValidationError` from PERT math validators (the model sometimes gets the arithmetic wrong — currently this causes a retry, but after max retries it should produce a clear error, not a stack trace).

#### 10.3 Integration tests

- [ ] Create `tests/integration/` with tests gated behind `pytest -m integration`:
  - **test_greenfield_e2e:** Run `showcase_forge_stream.py` with `--dry-run` equivalent (mock LLM but test real adapter + swarm wiring).
  - **test_provider_connectivity:** For each provider with a key set, make one real LLM call and verify response. Skip if no key.
  - **test_ragflow_connectivity:** If RAGFlow is running, verify sync → parse → search works.

#### 10.4 Documentation

- [ ] Write a `README.md` for the repo covering:
  - What it does (one paragraph)
  - Quick start (install, set keys, run)
  - Architecture diagram (text-based, showing the pipeline stages)
  - Quality tiers (standard vs premium)
  - Configuration reference (key env vars)

- [ ] Write `docs/USAGE.md` with detailed examples:
  - "I have a transcript" → greenfield workflow
  - "I have a codebase" → brownfield workflow
  - "I have both" → greyfield workflow
  - "This is a £1M+ project" → premium quality workflow

#### 10.5 Configuration refinement

- [ ] Make tier model lists configurable via `config.py` or a `model_tiers.yaml`. Currently hardcoded in `router.py`. For v1.0, the user should be able to swap in different models without editing code.

- [ ] Add a `META_FACTORY_QUALITY` env var (default: `standard`) so premium mode can be the default for a team that always works on large projects.

- [ ] Verify all default models still exist and haven't been deprecated. LLM providers rotate model names frequently.

#### 10.6 v1.0 acceptance criteria

The system is v1.0 when all of these pass:

- [ ] `python main.py --input transcript.txt --client "X" --quality standard` produces a phased proposal (POC + MVP + V1) with PERT estimates and confidence intervals in under 5 minutes.
- [ ] `python main.py --input transcript.txt --client "X" --quality premium` produces a higher-quality proposal using hybrid context + ensemble estimation.
- [ ] Every proposal has at least 2 delivery phases. The first phase is ≤6 weeks. Each phase has success criteria and `can_stop_here` is set correctly.
- [ ] The hybrid context mode produces a Dossier that's demonstrably more complete than RAG-only (test with a document where RAG misses something).
- [ ] The ensemble estimation produces a range, not a point estimate, with the correct PERT math.
- [ ] All three swarm modes (greenfield, brownfield, greyfield) run successfully.
- [ ] Tier routing is correct: tier0 for Oracle, tier1 for extraction, tier2 for critics, tier3 for synthesis.
- [ ] Cost is tracked and reported accurately. `--hourly-rate` affects the per-phase GBP estimates.
- [ ] `pytest` passes with no failures.
- [ ] A non-developer can read `README.md` and run their first engagement in under 10 minutes.
- [ ] The output for a small transcript (~5K tokens, £50K engagement) is a concise 2-phase plan, not a 30-page document.

---

## Known Issues & Tech Debt

| Issue | Priority | Notes |
|-------|----------|-------|
| **CriticAgent doesn't actually route through tier2** | **High — Phase 5.1** | `self.model` is set to provider default, not `"tier2"`. Metadata says tier2 but model routing bypasses the Router. Fix in Phase 5.1. |
| **`BaseAgent.run()` can't override model per call** | **High — Phase 5.2** | No `model` parameter on `run()`. Needed for tier escalation. Fix in Phase 5.2. |
| **`_enrich_with_feedback` may break on strict models** | Medium | Adds `previous_feedback` key to input dict, then calls `model_validate()`. If the input model doesn't allow extra fields, this fails silently or raises. Verify contracts have `extra="allow"` or use a different enrichment strategy. |
| Old `providers/` files (anthropic, openai, gemini, deepseek) | Low | Unused since Phase 2. Can delete anytime. |
| `TokenUsage.total_cost` calls `settings.calculate_cost()` | Low | Legacy token math in `base_agent.py`. Harmless — real cost from `SwarmCostLogger`. Delete `calculate_cost()` and related config fields when convenient. |
| `list_providers()` uses legacy provider classes | Low | `factory.py:62-78`. Still instantiates old provider classes for availability. Could use `litellm.check_valid_key()` instead. |
| Ensemble estimation not implemented | Medium | Original vision calls for Optimist/Pessimist/Realist sub-agents with programmatic PERT aggregation. Current `EstimatorAgent` is single-pass. Consider for Phase 6. |
| Python 3.9 on host | Low | RAGFlow SDK needs 3.12+ (we use HTTP fallback). Consider upgrading venv. |
| `run_factory()` passes provider/model redundantly | Low | Passed to both `EngagementManager.__init__()` and `.run()`. Harmless but confusing. |
| Tests are mock-heavy, no integration tests | Medium | Consider one optional integration test per provider gated behind `--integration` flag. |
| RAGFlow SDK path (`_*_sdk` methods) is untested | Low | We only use HTTP fallback. SDK methods may have bit-rotted. |
| Tier model list hardcoded in `router.py` | Low | Not yet configurable via config/yaml. Fine for prototyping. |

---

## Instructions for Cursor / Claude Code

1. **Phases 1–4 are done. Start with Phase 5.**
2. **Use LiteLLM for everything LLM-related.** Cost tracking, retries, fallbacks, model routing — do not reimplement these.
3. **Keep the `LLMProvider` interface.** Agents call `self.llm_provider.complete()`. The provider is backed by `litellm.completion()`.
4. **Phase 5 touches few files.** The changes are: `agents/critic_agent.py` (fix model resolution), `agents/base_agent.py` (add `model` param to `run()`), `swarms/base_swarm.py` (escalation logic in `run_with_critique()`), `providers/cost_logger.py` (budget warning), `config.py` (warning threshold), and tests.
5. **CriticAgent does NOT inherit from BaseAgent.** It's its own class. When fixing tier routing (5.1), change `self.model` directly — don't try to refactor CriticAgent to extend BaseAgent.
6. **Tier strings are model names for the Router.** When `LiteLLMProvider.complete()` receives `model="tier2"`, it detects the tier name and routes through `get_router().completion()`. Any other model string goes directly to `litellm.completion()`. This is how tier routing works — no special API needed.
7. **The `model` parameter on `run()` is for one-shot overrides.** Don't change `self.model` permanently. The escalation passes `model="tier3"` to a single `run()` call; subsequent calls (if any) should revert to the agent's default tier.
8. **Test each step** before moving on. Mocked unit tests are fine. Run `python scripts/showcase_forge_stream.py --dry-run` (no LLM needed) for adapter tests, then with `-p openai` for full pipeline.
9. **Do not modify RAGFlow config or Docker files.** The RAGFlow setup is stable.
10. **Model IDs matter.** Use LiteLLM model strings from the table above. The format is `provider/model-name`.

---

## Next Step

> Start with **Phase 5.1**: Fix `CriticAgent` model resolution in `agents/critic_agent.py` (change `self.model = model or self.llm_provider.default_model` to `self.model = model or "tier2"`). Then **5.2**: add `model` param to `BaseAgent.run()`. Then **5.3**: wire escalation logic into `run_with_critique()`. Test with `pytest tests/test_quality_gate.py`. Verify end-to-end with `python scripts/showcase_forge_stream.py -p openai`.

---

## Vision Alignment & What Comes Next

This section maps the Forge-Stream phases to the original "Autonomous Consultancy Swarm" architecture (from the deep research document) to ensure we're building toward the right destination.

### Original vision → Current state

| Original Vision Element | Status | Where |
|---|---|---|
| Hub-and-Spoke state machine (`EngagementManager`) | Done | `orchestrator/engagement_manager.py` |
| Router detects input type (CODE/TRANSCRIPT/IDEA) | Done | `router/` with classifier → Mode enum |
| Greenfield / Brownfield / Greyfield swarms | Done | `swarms/greenfield.py`, `brownfield.py`, `greyfield.py` |
| "Bible" context stuffing per agent | Done | `Librarian` + `AGENT_BIBLE_MAPPING` in `config.py` |
| Adversarial Critic after every stage | Done | `CriticAgent` + `run_with_critique()` |
| Pydantic contracts for all handoffs | Done | `contracts/` |
| RAG pipeline (solves "Context Stuffing vs RAG" risk) | Done | RAGFlow + `librarian/rag_client.py` |
| Dossier compression (Miner → structured intermediate) | Done | `agents/miner_agent.py` + `swarms/ingestion_swarm.py` |
| LiteLLM cost control + tier routing | Done | `providers/litellm_provider.py` + `providers/router.py` |
| Tiered critic loop with tier escalation | **Phase 5** | `swarms/base_swarm.py` |
| **Ensemble Estimation** (Optimist/Pessimist/Realist + PERT) | **Not started** | Single `EstimatorAgent` exists; ensemble pattern deferred |
| **"Feed it anything" end-to-end** | **Infrastructure done, UX not polished** | All modes work but CLI is demo-oriented, not product-ready |

### What Forge-Stream added beyond the original vision

The Gemini deep research document assumed agents would read full books from context and didn't address cost, token limits, or model selection. Forge-Stream solved these:

1. **RAG over Context Stuffing** — The deep research flagged "Lost in the Middle" syndrome as a risk of loading entire books. RAGFlow retrieves only relevant chunks. The Librarian loads cheat sheets (condensed summaries), not full texts, into agent prompts.

2. **The Miner / Dossier layer** — Not in the original vision. It inserts a cheap extraction step (tier1) that compresses RAG output into a structured `ProjectDossier`, reducing token consumption for all downstream agents. This is the "Cascading Model Architecture" — cheap models do grunt work, expensive models do synthesis.

3. **LiteLLM with tier routing** — The original vision didn't address cost control. LiteLLM gives us per-call cost tracking, budget caps, model fallbacks, and tier-based routing without building any of it ourselves.

### Roadmap to v1.0

| Phase | Focus | Key Deliverable | Value |
|-------|-------|-----------------|-------|
| **5** | Quality Gate | Tiered critic loop with tier escalation | Critics actually use tier2; failed agents escalate to tier3 |
| **6** | Hybrid Context | Full-context + RAG + reconciliation | Best possible Dossier quality for £1M+ projects |
| **7** | Ensemble Estimation | Optimist/Pessimist/Realist + PERT aggregation | Statistically reliable cost estimates |
| **8** | All Paths | Brownfield/Greyfield with Dossier integration | System handles any input type |
| **9** | Phased Delivery & CLI | POC→MVP→V1 output structure, `--quality`, `--hourly-rate` | Right-sized proposals for any engagement |
| **10** | Production Hardening | Tests, docs, error handling, config | Ready for real client engagements |

**After v1.0 (not planned yet):**
- Web UI / API server for team use
- Historical project database for reference class forecasting
- Automated Bible updates (new editions, new frameworks)
- Multi-engagement portfolio view (cost aggregation across projects)
- Client-facing report generation (PDF export)
