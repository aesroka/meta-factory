"""Miner Agent - Fact Extractor.

Reads RAG-retrieved context and produces a structured ProjectDossier (Phase 3).
Uses Tier 1 models; input is pre-fetched RAG context, not raw transcripts.
"""

from typing import Optional, List

from agents.base_agent import BaseAgent
from librarian import Librarian
from contracts import ProjectDossier, MinerInput


# RAG queries mapped to Dossier fields (3.3). Miner sees all results concatenated.
MINER_RAG_QUERIES: List[str] = [
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


class MinerAgent(BaseAgent):
    """Fact Extractor: turns RAG chunks into a validated ProjectDossier."""

    SYSTEM_PROMPT = """You are a Fact Extractor. Your job is to read RAG-retrieved context about a project
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
7. Respond with ONLY valid JSON. No prose, no markdown fences, no explanation."""

    DEFAULT_TIER = "tier1"

    def __init__(
        self,
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Initialize the Miner Agent."""
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

    def extract(
        self,
        rag_context: str,
        client_name: str,
        mode: Optional[str] = None,
    ) -> ProjectDossier:
        """Run the Miner on pre-fetched RAG context.

        Args:
            rag_context: Concatenated RAG chunks (e.g. from MINER_RAG_QUERIES).
            client_name: Client or project name (used for project_name).
            mode: Optional greenfield, brownfield, or greyfield.

        Returns:
            Validated ProjectDossier.
        """
        input_data = MinerInput(
            rag_context=rag_context,
            client_name=client_name,
            mode=mode,
        )
        result = self.run(input_data, max_retries=2)
        return result.output
