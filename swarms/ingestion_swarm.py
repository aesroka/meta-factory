"""Ingestion Swarm (Phase 3): RAG → Miner → ProjectDossier.

Retrieves context with MINER_RAG_QUERIES, runs MinerAgent with critic review,
produces a validated ProjectDossier as the compressed input for downstream agents.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from swarms.base_swarm import BaseSwarm
from librarian import Librarian
from agents import MinerAgent, MINER_RAG_QUERIES
from contracts import MinerInput, ProjectDossier


@dataclass
class IngestionInput:
    """Input for the Ingestion Swarm."""

    client_name: str
    dataset_id: Optional[str] = None
    mode: Optional[str] = None


class IngestionSwarm(BaseSwarm):
    """RAG retrieval + Miner agent with critic → ProjectDossier."""

    @property
    def mode_name(self) -> str:
        return "ingestion"

    def execute(self, input_data: IngestionInput) -> Dict[str, Any]:
        """Run RAG retrieval then Miner (with critic)."""
        rag_context = self._retrieve_context(input_data.dataset_id)
        if not rag_context:
            return self._finalize_run("error")

        dossier = self._run_miner(rag_context, input_data)
        if self._cost_exceeded:
            return self._finalize_run("cost_exceeded")

        return self._finalize_run("completed")

    def _retrieve_context(self, dataset_id: Optional[str] = None, top_k: int = 5) -> str:
        """Run MINER_RAG_QUERIES against RAGFlow and concatenate results."""
        from agents.tools.rag_search import rag_search

        sections = []
        for q in MINER_RAG_QUERIES:
            chunks = rag_search(q, dataset_id=dataset_id, top_k=top_k)
            if not chunks:
                continue
            parts = [f"## Query: {q!r}\n"]
            for i, c in enumerate(chunks, 1):
                content = (c.get("content") or "").strip()
                sim = c.get("similarity")
                if sim is not None:
                    parts.append(f"[{i}] (similarity={sim:.2f})\n{content}\n\n")
                else:
                    parts.append(f"[{i}]\n{content}\n\n")
            sections.append("".join(parts))
        if not sections:
            return ""
        return "\n---\n\n".join(sections)

    def _run_miner(self, rag_context: str, input_data: IngestionInput) -> ProjectDossier:
        """Run MinerAgent with critic review; return the Dossier (or best-effort on escalation)."""
        agent = MinerAgent(
            librarian=self.librarian,
            provider=self.provider,
            model=self.model,
        )
        agent_input = MinerInput(
            rag_context=rag_context,
            client_name=input_data.client_name,
            mode=input_data.mode,
        )
        output, _passed, _escalation = self.run_with_critique(
            agent=agent,
            input_data=agent_input,
            stage_name="mining",
        )
        return output

    def _finalize_run(self, status: str) -> Dict[str, Any]:
        """Finalize the run and return results."""
        self.run.status = status
        self.run.completed_at = datetime.now()

        output_path = self.save_artifacts()

        result = {
            "run_id": self.run.run_id,
            "status": status,
            "output_path": output_path,
            "artifacts": self.run.artifacts,
            "escalations": self.run.escalations,
            "token_usage": {
                "input_tokens": self.run.token_usage.input_tokens,
                "output_tokens": self.run.token_usage.output_tokens,
                "cost_usd": self.run.token_usage.total_cost,
            },
        }
        if self.run.error is not None:
            result["error"] = self.run.error or "Unknown error"
        return result
