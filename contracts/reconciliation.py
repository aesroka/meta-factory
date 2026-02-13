"""Dossier reconciliation contract (Phase 6: Hybrid Context)."""

from typing import List
from pydantic import BaseModel, Field

from .project import ProjectDossier


class DossierReconciliation(BaseModel):
    """Result of comparing RAG-extracted and full-context Dossiers."""

    merged_dossier: ProjectDossier
    agreements: List[str] = Field(
        default_factory=list,
        description="Fields or items where both sources agree",
    )
    disagreements: List[str] = Field(
        default_factory=list,
        description="Fields where sources differ — flagged for review",
    )
    rag_only_items: List[str] = Field(
        default_factory=list,
        description="Items found only via RAG",
    )
    full_context_only_items: List[str] = Field(
        default_factory=list,
        description="Items found only via full-context",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the merged dossier",
    )
