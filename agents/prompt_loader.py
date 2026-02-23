"""Load agent prompts from YAML files with variant support (Phase 13)."""

import os
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel


class PromptVariant(BaseModel):
    """A single prompt variant."""
    system_prompt: str


class PromptFile(BaseModel):
    """Contents of a prompt YAML file."""
    version: str
    system_prompt: str
    variants: Dict[str, PromptVariant] = {}
    examples: list = []
    metadata: dict = {}


class PromptLoader:
    """Load agent prompts from YAML files."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or Path(__file__).parent / "prompts"
        self._cache: Dict[str, PromptFile] = {}

    def load(self, agent_role: str, variant: str = "default") -> str:
        """Load prompt for agent role, optionally selecting a variant.

        Args:
            agent_role: Agent role (discovery, architect, etc.)
            variant: Prompt variant name (default, concise, experimental, etc.)

        Returns:
            System prompt string
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for prompt loading. pip install pyyaml")
        if agent_role not in self._cache:
            prompt_path = self.prompts_dir / f"{agent_role}.yaml"
            if not prompt_path.exists():
                raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
            raw = yaml.safe_load(prompt_path.read_text())
            self._cache[agent_role] = PromptFile(**raw)
        pf = self._cache[agent_role]
        if variant in pf.variants:
            return pf.variants[variant].system_prompt
        return pf.system_prompt

    def list_variants(self, agent_role: str) -> list:
        """List available variant names for an agent."""
        try:
            import yaml
        except ImportError:
            return ["default"]
        if agent_role not in self._cache:
            prompt_path = self.prompts_dir / f"{agent_role}.yaml"
            if not prompt_path.exists():
                return []
            raw = yaml.safe_load(prompt_path.read_text())
            self._cache[agent_role] = PromptFile(**raw)
        return list(self._cache[agent_role].variants.keys()) or ["default"]


_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Singleton prompt loader."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader
