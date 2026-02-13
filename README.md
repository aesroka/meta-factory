# Meta-Factory for Software Consultancy

An autonomous AI system that ingests diverse inputs (rough ideas, transcripts, existing codebases) and orchestrates specialised multi-agent swarms to produce production-ready software proposals.

## Architecture

### Hub-and-Spoke State Machine

- **Router**: Analyses input and selects the correct swarm strategy
- **Engagement Manager**: Orchestrates agent execution within each swarm
- **Librarian**: Injects domain-specific knowledge ("Bibles") into agents at runtime
- **Critic Nodes**: Review every major artifact before it passes downstream
- **Pydantic Contracts**: All agents communicate via strict typed contracts

### The Three Modes

| Mode | Trigger | Swarm |
|------|---------|-------|
| **Greenfield** | Transcripts, ideas, new project briefs | Consultancy Swarm |
| **Brownfield** | Existing codebase, legacy rescue | Archaeologist Swarm |
| **Greyfield** | Existing platform + new requirements | Hybrid Swarm |

### Forge-Stream: Dossier-Primed Pipeline

Experts (Discovery, Architect, Estimator, Synthesis, Proposal) can run from a **structured dossier** instead of raw content:

1. **Ingestion** (optional): RAG → Miner Agent → **ProjectDossier** (stakeholders, tech stack, constraints, logic flows, legacy debt).
2. **Adapter**: `dossier_to_discovery_input(dossier)` turns the dossier into a single markdown transcript for Discovery.
3. **Greenfield**: Same pipeline (Discovery → Architect → … → Proposal); input is either raw transcript or dossier. When a dossier is provided, Discovery and downstream agents see the structured transcript, not raw RAG chunks—typically **cheaper** (fewer tokens) and more consistent.

See **[FORGE-STREAM-PLAN.md](FORGE-STREAM-PLAN.md)** for the full roadmap.

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick start

Set an LLM API key (e.g. `OPENAI_API_KEY`) in `.env`, then:

```bash
python main.py --input ./workspace/sample_transcript.txt --client "Acme" --quality standard
```

## Quality tiers

| Tier | Use case | Behaviour |
|------|----------|-----------|
| **standard** | Exploratory, small engagements (~£50K) | RAG-only context, single estimator, tier1/tier3 routing. ~$1–5/run. |
| **premium** | High-value engagements (£500K+) | Hybrid context (RAG + full-context), ensemble estimation (Optimist/Pessimist/Realist), tier0/tier3. ~$30–50/run. |

```bash
python main.py --input ./transcript.txt --client "Acme" --quality premium
python main.py --input ./transcript.txt --client "Acme" --hourly-rate 200
```

## Usage

```bash
# Auto-detect mode
python main.py --input ./client_transcripts/

# Force a mode
python main.py --input ./legacy_codebase/ --mode brownfield

# Greyfield with both inputs
python main.py --input ./client_transcripts/ --codebase ./legacy_codebase/ --mode greyfield
```

## Demos & Scripts

### Forge-Stream showcase (no RAGFlow)

Runs the **dossier-primed pipeline** using curated sample data from `workspace/` (no RAG sync or API key required for dry-run):

```bash
# Adapter + transcript only (no LLM calls)
python scripts/showcase_forge_stream.py --dry-run

# Full pipeline: Dossier → Discovery → Architect → … → Proposal (needs LLM API key)
python scripts/showcase_forge_stream.py

# Use another provider
python scripts/showcase_forge_stream.py -p gemini
```

Shows: Step 1 Dossier (as if from Miner), Step 2 Adapter output (structured transcript), Step 3 Greenfield run with cost breakdown.

### RAGFlow + agents (full Forge-Stream)

Requires **RAGFlow** and an **LLM provider** (OpenAI, Gemini, etc.). See **[docs/RAGFLOW_SETUP.md](docs/RAGFLOW_SETUP.md)** for Docker, API key, and `.env` configuration. Put `.txt`/`.md` files in `workspace/` (e.g. `workspace/sample_transcript.txt`, `workspace/sample_notes.txt`).

```bash
# Sync workspace → RAG → example searches only
python scripts/rag_demo.py

# RAG → Discovery only (cheap)
python scripts/rag_agent_demo.py

# RAG → full Greenfield (transcript as input)
python scripts/rag_agent_demo.py --full

# RAG → Miner → Dossier only
python scripts/rag_agent_demo.py --mode dossier

# RAG → Miner → Dossier → full Greenfield (dossier-primed pipeline)
python scripts/rag_agent_demo.py --mode full-dossier

# Cost comparison: raw transcript path vs dossier path (target: dossier cheaper)
python scripts/rag_agent_demo.py --compare
```

`--mode`: `discovery` | `dossier` | `full` | `full-dossier`. Use `-p openai` / `-p gemini` etc. and optional `-m <model>`.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
meta-factory/
├── main.py              # CLI entry point
├── config.py            # Settings and configuration
├── router/              # Input classification and routing
├── librarian/           # Bible/framework knowledge management
├── contracts/            # Pydantic contracts; adapters.py = dossier → DiscoveryInput
├── agents/               # Individual agent implementations
├── swarms/               # Swarm orchestration (greenfield, brownfield, greyfield, ingestion)
├── orchestrator/         # Central state machine and cost control
├── workspace/            # Sample content; synced to RAGFlow for RAG demos
├── outputs/              # Run artifacts (discovery, architecture, proposal, etc.)
├── scripts/              # rag_demo.py, rag_agent_demo.py, showcase_forge_stream.py
├── tests/                # Test suite
└── FORGE-STREAM-PLAN.md  # Roadmap and phase details
```

## Build Phases

- [x] **Phase 1**: Contracts & Skeleton
- [x] **Phase 2**: The Librarian (Knowledge Layer)
- [x] **Phase 3**: Base Agent + Critic Loop
- [x] **Phase 4**: Swarm Implementations (Greenfield, Brownfield, Greyfield)
- [x] **Phase 4 (Forge-Stream)**: Expert Synthesis — Dossier-to-transcript adapter, GreenfieldInput(dossier=...), `full-dossier` demo, `--compare` cost comparison, tests (adapters + dossier pipeline)
- [ ] **Phase 5**: Quality Gate (tiered critic loop, escalation, budget warning)
- [x] **Phase 6**: CLI & Polish
- RAG integration: supported via Librarian + `rag_agent_demo.py` and `showcase_forge_stream.py`

## Environment Variables

Create a `.env` file (or export in the shell). At least one LLM provider is needed for full pipeline runs; RAG demos also need RAGFlow.

```bash
# LLM (use at least one; provider chosen via -p / --provider)
META_FACTORY_OPENAI_API_KEY=your_key_here
# META_FACTORY_ANTHROPIC_API_KEY=...
# META_FACTORY_GEMINI_API_KEY=...
# META_FACTORY_DEEPSEEK_API_KEY=...

# Optional
META_FACTORY_MAX_COST_PER_RUN_USD=5.00

# RAGFlow (required for rag_demo.py and rag_agent_demo.py)
META_FACTORY_RAGFLOW_API_KEY=your_ragflow_key
```

## Cost Control

The system tracks token usage and enforces cost limits:

- Default max cost per run: $5.00 USD
- Override with `--max-cost` flag or `META_FACTORY_MAX_COST_PER_RUN_USD` env var
- Circuit breaker stops execution if limit exceeded
- Cost manifest saved with each run

## Framework "Bibles"

The Librarian injects distilled framework knowledge into agents:

| Framework | Used By |
|-----------|---------|
| Mom Test | Discovery Agent |
| SPIN Selling | Discovery Agent |
| Feathers (Legacy Code) | Legacy Agent |
| Fowler (Refactoring) | Legacy Agent |
| C4 Model | Legacy Agent |
| EIP (Hohpe) | Architect Agent |
| ATAM | Architect Agent |
| McConnell Estimation | Estimator Agent |
| Minto Pyramid | Proposal Agent |
| SCQA Framework | Proposal Agent |
