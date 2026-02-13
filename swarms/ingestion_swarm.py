"""Ingestion Swarm (Phase 3 + 6): RAG and/or full-context → Miner → ProjectDossier.

Retrieves context with MINER_RAG_QUERIES (or uses raw_documents for full-context),
runs MinerAgent with critic review, produces a validated ProjectDossier.
Phase 6: context_mode rag|full|hybrid; hybrid runs both and reconciles.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from swarms.base_swarm import BaseSwarm
from librarian import Librarian
from agents import MinerAgent, MINER_RAG_QUERIES
from contracts import MinerInput, ProjectDossier, DossierReconciliation


@dataclass
class IngestionInput:
    """Input for the Ingestion Swarm."""

    client_name: str
    dataset_id: Optional[str] = None
    mode: Optional[str] = None
    context_mode: str = "rag"  # "rag", "full", or "hybrid"
    raw_documents: Optional[str] = None  # Concatenated raw text for full-context mode


class IngestionSwarm(BaseSwarm):
    """RAG and/or full-context + Miner agent with critic → ProjectDossier."""

    @property
    def mode_name(self) -> str:
        return "ingestion"

    def execute(self, input_data: IngestionInput) -> Dict[str, Any]:
        """Run by context_mode: rag (RAG only), full (full-context only), or hybrid (both + reconcile)."""
        dossier: Optional[ProjectDossier] = None
        if input_data.context_mode == "rag":
            dossier = self._run_rag_pipeline(input_data)
        elif input_data.context_mode == "full":
            if not input_data.raw_documents:
                self.run.error = "context_mode=full requires raw_documents"
                return self._finalize_run("error")
            dossier = self._full_context_extract(input_data.raw_documents, input_data)
        elif input_data.context_mode == "hybrid":
            if not input_data.raw_documents:
                self.run.error = "context_mode=hybrid requires raw_documents"
                return self._finalize_run("error")
            rag_dossier = self._run_rag_pipeline(input_data)
            full_dossier = self._full_context_extract(input_data.raw_documents, input_data)
            if rag_dossier is None:
                # RAG returned nothing (e.g. empty dataset); use full-context result only
                self.run.artifacts["dossier_rag"] = None
                self.run.artifacts["dossier_full"] = full_dossier
                dossier = full_dossier
            else:
                recon = self._reconcile_dossiers(rag_dossier, full_dossier, input_data)
                self.run.artifacts["dossier_rag"] = rag_dossier
                self.run.artifacts["dossier_full"] = full_dossier
                self.run.artifacts["reconciliation"] = recon
                dossier = recon.merged_dossier
        else:
            self.run.error = f"Unknown context_mode: {input_data.context_mode}"
            return self._finalize_run("error")

        if self._cost_exceeded:
            return self._finalize_run("cost_exceeded")
        if dossier is None:
            return self._finalize_run("error")

        self.run.artifacts["mining"] = dossier
        return self._finalize_run("completed")

    def _run_rag_pipeline(self, input_data: IngestionInput) -> Optional[ProjectDossier]:
        """RAG retrieval + Miner with critic; returns dossier or None on failure."""
        rag_context = self._retrieve_context(input_data.dataset_id)
        if not rag_context:
            return None
        return self._run_miner(rag_context, input_data)

    def _full_context_extract(self, raw_documents: str, input_data: IngestionInput) -> ProjectDossier:
        """Run MinerAgent with full document context using tier0 model."""
        agent = MinerAgent(
            librarian=self.librarian,
            provider=self.provider,
            model="tier0",
        )
        return agent.extract(
            rag_context=raw_documents,
            client_name=input_data.client_name,
            mode=input_data.mode,
        )

    def _reconcile_dossiers(
        self,
        rag_dossier: ProjectDossier,
        full_dossier: ProjectDossier,
        input_data: IngestionInput,
    ) -> DossierReconciliation:
        """Merge RAG and full-context dossiers; compute agreements/disagreements (heuristic)."""
        agreements: List[str] = []
        disagreements: List[str] = []
        rag_only: List[str] = []
        full_only: List[str] = []

        # Stakeholders: by name
        rag_names = {s.name.lower() for s in rag_dossier.stakeholders}
        full_names = {s.name.lower() for s in full_dossier.stakeholders}
        for n in rag_names & full_names:
            agreements.append(f"stakeholder:{n}")
        for n in rag_names - full_names:
            rag_only.append(f"stakeholder:{n}")
        for n in full_names - rag_names:
            full_only.append(f"stakeholder:{n}")

        # Tech stack: union
        rag_tech = set(rag_dossier.tech_stack_detected)
        full_tech = set(full_dossier.tech_stack_detected)
        for t in rag_tech & full_tech:
            agreements.append(f"tech:{t}")
        for t in rag_tech - full_tech:
            rag_only.append(f"tech:{t}")
        for t in full_tech - rag_tech:
            full_only.append(f"tech:{t}")

        merged_stakeholders = list(rag_dossier.stakeholders)
        for s in full_dossier.stakeholders:
            if s.name.lower() not in {x.name.lower() for x in merged_stakeholders}:
                merged_stakeholders.append(s)

        merged_tech = list(rag_tech | full_tech)
        merged_constraints = list(rag_dossier.constraints)
        for c in full_dossier.constraints:
            key = (c.category, c.requirement)
            if key not in {(x.category, x.requirement) for x in merged_constraints}:
                merged_constraints.append(c)
        merged_flows = list(rag_dossier.logic_flows)
        for f in full_dossier.logic_flows:
            if f.trigger not in {x.trigger for x in merged_flows}:
                merged_flows.append(f)

        merged_summary = rag_dossier.summary
        if len(full_dossier.summary) > len(rag_dossier.summary):
            merged_summary = full_dossier.summary
        merged_legacy = full_dossier.legacy_debt_summary or rag_dossier.legacy_debt_summary

        total_items = len(agreements) + len(disagreements) + len(rag_only) + len(full_only)
        confidence = 1.0 - (len(disagreements) / max(1, total_items))

        merged_dossier = ProjectDossier(
            project_name=rag_dossier.project_name or full_dossier.project_name,
            summary=merged_summary,
            stakeholders=merged_stakeholders,
            tech_stack_detected=merged_tech,
            constraints=merged_constraints,
            logic_flows=merged_flows,
            legacy_debt_summary=merged_legacy,
        )

        return DossierReconciliation(
            merged_dossier=merged_dossier,
            agreements=agreements,
            disagreements=disagreements,
            rag_only_items=rag_only,
            full_context_only_items=full_only,
            confidence_score=round(confidence, 2),
        )

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
