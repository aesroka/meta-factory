"""Librarian module for loading Bible knowledge into agents.

The Librarian provides a two-tier knowledge system:
1. Cheat Sheets (always loaded) - 2-page framework summaries
2. RAG retrieval (on-demand) - RAGFlow workspace sync and search (Forge-Stream Phase 1)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from config import settings, AGENT_BIBLE_MAPPING


# File extensions to sync from workspace to RAGFlow
WORKSPACE_SYNC_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".java", ".go", ".rs", ".rb",
    ".php", ".cs", ".cpp", ".c", ".h", ".json", ".yaml", ".yml", ".html",
}


class Librarian:
    """Loads Bible knowledge for agents.

    Two-tier system:
    1. Cheat Sheets (always loaded into context) — small, framework-level
    2. RAG retrieval (on-demand) — specific passages from full texts

    For MVP (Phase 2), implements cheat sheets only.
    RAG integration is Phase 5.
    """

    def __init__(self, cheat_sheets_dir: Optional[str] = None, rag_client: Optional[Any] = None):
        """Initialize the Librarian.

        Args:
            cheat_sheets_dir: Path to cheat sheets directory.
                            Defaults to config setting.
            rag_client: Optional RAGFlow client for sync_workspace and get_rag_passages.
        """
        self.cheat_sheets_dir = Path(cheat_sheets_dir or settings.cheat_sheets_dir)
        self._cheat_sheet_cache: Dict[str, str] = {}
        self._rag_client = rag_client
        self._load_cheat_sheets()

    def _load_cheat_sheets(self) -> None:
        """Load all cheat sheets into memory cache."""
        if not self.cheat_sheets_dir.exists():
            raise FileNotFoundError(f"Cheat sheets directory not found: {self.cheat_sheets_dir}")

        for md_file in self.cheat_sheets_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                self._cheat_sheet_cache[md_file.name] = content
            except Exception as e:
                print(f"Warning: Could not load {md_file}: {e}")

    def get_cheat_sheet(self, name: str) -> str:
        """Get a single cheat sheet by name.

        Args:
            name: Cheat sheet filename (e.g., 'mom_test.md')

        Returns:
            The cheat sheet content.

        Raises:
            KeyError: If cheat sheet not found.
        """
        if name not in self._cheat_sheet_cache:
            raise KeyError(f"Cheat sheet not found: {name}")
        return self._cheat_sheet_cache[name]

    def get_context_for_agent(self, agent_role: str) -> str:
        """Returns the combined cheat sheet text for a given agent role.

        Mapping:
        - discovery -> mom_test.md + spin_selling.md
        - legacy -> legacy_code_feathers.md + c4_model.md + refactoring_fowler.md
        - architect -> eip_hohpe.md + atam.md
        - estimator -> mcconnell_estimation.md
        - proposal -> minto_pyramid.md + scqa_framework.md
        - critic -> loads the SAME bibles as the agent it's reviewing

        Args:
            agent_role: The role of the agent (e.g., 'discovery', 'architect')

        Returns:
            Combined text of all relevant cheat sheets.

        Raises:
            ValueError: If agent role is not recognized.
        """
        role = agent_role.lower()

        if role not in AGENT_BIBLE_MAPPING:
            raise ValueError(
                f"Unknown agent role: {agent_role}. "
                f"Valid roles: {list(AGENT_BIBLE_MAPPING.keys())}"
            )

        bible_files = AGENT_BIBLE_MAPPING[role]
        return self._combine_cheat_sheets(bible_files)

    def get_context_for_critic(self, reviewing_agent_role: str) -> str:
        """Get context for a critic reviewing a specific agent's output.

        The critic receives the same Bible context as the agent being reviewed,
        so it can evaluate compliance with the relevant frameworks.

        Args:
            reviewing_agent_role: The role of the agent being reviewed.

        Returns:
            Combined text of relevant cheat sheets.
        """
        return self.get_context_for_agent(reviewing_agent_role)

    def _combine_cheat_sheets(self, file_names: List[str]) -> str:
        """Combine multiple cheat sheets into a single context string.

        Args:
            file_names: List of cheat sheet filenames to combine.

        Returns:
            Combined text with clear separators.
        """
        sections = []
        for name in file_names:
            try:
                content = self.get_cheat_sheet(name)
                sections.append(f"{'='*60}\n{name.upper()}\n{'='*60}\n\n{content}")
            except KeyError:
                print(f"Warning: Cheat sheet not found: {name}")

        return "\n\n".join(sections)

    def list_available_cheat_sheets(self) -> List[str]:
        """List all available cheat sheet names.

        Returns:
            List of cheat sheet filenames.
        """
        return list(self._cheat_sheet_cache.keys())

    def get_all_context(self) -> str:
        """Get all cheat sheets combined (for debugging/testing).

        Returns:
            All cheat sheets combined into one string.
        """
        return self._combine_cheat_sheets(list(self._cheat_sheet_cache.keys()))

    def sync_workspace(
        self,
        workspace_dir: Optional[Path] = None,
        dataset_name: Optional[str] = None,
        wait_parsed: bool = True,
        parse_timeout_sec: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Sync workspace folder to RAGFlow: scan, upload new files, trigger DDU parsing.

        Recursively scans workspace for transcripts, docs, and code; uploads to a
        RAGFlow dataset and triggers Deep Document Understanding (DDU) parsing.

        Args:
            workspace_dir: Directory to scan. Defaults to settings.workspace_dir.
            dataset_name: RAGFlow dataset name. Defaults to settings.ragflow_dataset_name.
            wait_parsed: If True, block until all uploaded documents are parsed.
            parse_timeout_sec: Max seconds to wait for parsing (default from settings).

        Returns:
            Dict with uploaded_count, document_ids, dataset_id, and optional parse results.

        Raises:
            RuntimeError: If RAGFlow is not configured (no API key).
        """
        from librarian.rag_client import RAGFlowClient

        if not settings.ragflow_api_key:
            raise RuntimeError("RAGFlow API key not set (META_FACTORY_RAGFLOW_API_KEY)")

        workspace_path = Path(workspace_dir or settings.workspace_dir)
        if not workspace_path.exists():
            return {"uploaded_count": 0, "document_ids": [], "dataset_id": None, "message": "workspace dir not found"}

        client = self._rag_client or RAGFlowClient()
        if not client.is_available():
            raise RuntimeError("RAGFlow client not available (check API key and URL)")

        dataset_id = client.ensure_dataset(dataset_name)
        uploaded: List[str] = []
        files_to_upload: List[tuple] = []

        for path in sorted(workspace_path.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in WORKSPACE_SYNC_EXTENSIONS:
                continue
            try:
                blob = path.read_bytes()
                files_to_upload.append((path, blob))
            except Exception:
                continue

        for path, blob in files_to_upload:
            try:
                doc_id = client.upload_document(
                    dataset_id=dataset_id,
                    content=blob,
                    display_name=path.name,
                )
                uploaded.append(doc_id)
            except Exception as e:
                raise RuntimeError(f"Upload failed for {path.name}: {e}") from e

        result: Dict[str, Any] = {
            "uploaded_count": len(uploaded),
            "document_ids": uploaded,
            "dataset_id": dataset_id,
        }
        if wait_parsed and uploaded:
            result["parse_results"] = client.wait_for_parsed(
                dataset_id=dataset_id,
                document_ids=uploaded,
                timeout_sec=parse_timeout_sec,
            )
        return result

    def get_rag_passages(self, query: str, agent_role: str, top_k: int = 5) -> List[str]:
        """RAG search over the workspace dataset (RAGFlow). Returns list of chunk texts.

        If RAGFlow is not configured or unavailable, returns empty list (no error).

        Args:
            query: The search query.
            agent_role: Agent role for context filtering (reserved for future use).
            top_k: Number of passages to return.
        """
        if not settings.ragflow_api_key:
            return []
        from librarian.rag_client import RAGFlowClient

        client = self._rag_client or RAGFlowClient()
        if not client.is_available():
            return []
        try:
            chunks = client.search(query=query, top_k=top_k)
            return [c.get("content", "") or "" for c in chunks if c.get("content")]
        except Exception:
            return []


# Convenience function for simple usage
def get_librarian() -> Librarian:
    """Get a singleton Librarian instance."""
    if not hasattr(get_librarian, "_instance"):
        get_librarian._instance = Librarian()
    return get_librarian._instance
