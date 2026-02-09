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

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
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
├── contracts/           # Pydantic contracts for all data flows
├── agents/              # Individual agent implementations
├── swarms/              # Swarm orchestration (greenfield, brownfield, greyfield)
├── orchestrator/        # Central state machine and cost control
├── workspace/           # Runtime artifact storage
├── outputs/             # Final deliverables
└── tests/               # Test suite
```

## Build Phases

- [x] **Phase 1**: Contracts & Skeleton (28 tests)
- [x] **Phase 2**: The Librarian (Knowledge Layer) (21 tests)
- [x] **Phase 3**: Base Agent + Critic Loop (9 tests)
- [x] **Phase 4**: Swarm Implementations (13 tests)
- [ ] **Phase 5**: RAG Integration (future)
- [x] **Phase 6**: CLI & Polish

## Environment Variables

Set your Anthropic API key before running:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Or create a `.env` file:

```
META_FACTORY_ANTHROPIC_API_KEY=your_key_here
META_FACTORY_MAX_COST_PER_RUN_USD=5.00
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
