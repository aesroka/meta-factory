"""Librarian module for loading Bible knowledge into agents.

The Librarian provides a two-tier knowledge system:
1. Cheat Sheets (always loaded) - 2-page framework summaries
2. RAG retrieval (on-demand) - specific passages from full texts (Phase 5)
"""

from pathlib import Path
from typing import Dict, List, Optional
from config import settings, AGENT_BIBLE_MAPPING


class Librarian:
    """Loads Bible knowledge for agents.

    Two-tier system:
    1. Cheat Sheets (always loaded into context) — small, framework-level
    2. RAG retrieval (on-demand) — specific passages from full texts

    For MVP (Phase 2), implements cheat sheets only.
    RAG integration is Phase 5.
    """

    def __init__(self, cheat_sheets_dir: Optional[str] = None):
        """Initialize the Librarian.

        Args:
            cheat_sheets_dir: Path to cheat sheets directory.
                            Defaults to config setting.
        """
        self.cheat_sheets_dir = Path(cheat_sheets_dir or settings.cheat_sheets_dir)
        self._cheat_sheet_cache: Dict[str, str] = {}
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

    def get_rag_passages(self, query: str, agent_role: str, top_k: int = 5) -> List[str]:
        """Phase 5: Vector search against full Bible texts.

        Args:
            query: The search query.
            agent_role: Agent role for context filtering.
            top_k: Number of passages to return.

        Raises:
            NotImplementedError: RAG integration is Phase 5.
        """
        raise NotImplementedError("RAG integration is Phase 5")


# Convenience function for simple usage
def get_librarian() -> Librarian:
    """Get a singleton Librarian instance."""
    if not hasattr(get_librarian, "_instance"):
        get_librarian._instance = Librarian()
    return get_librarian._instance
