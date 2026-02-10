"""Configuration settings for the Meta-Factory system."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List
from pathlib import Path


class Settings(BaseSettings):
    """Global settings for Meta-Factory.

    Settings can be overridden via environment variables with META_FACTORY_ prefix.
    Example: META_FACTORY_MAX_COST_PER_RUN_USD=10.00
    """

    # Model config
    default_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Default model for agent calls"
    )
    critic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Model used for critic reviews"
    )

    # Cost controls
    max_tokens_per_agent_call: int = Field(
        default=4096,
        description="Maximum tokens per individual agent call"
    )
    max_cost_per_run_usd: float = Field(
        default=5.00,
        description="Maximum total cost per run in USD"
    )
    max_critic_iterations: int = Field(
        default=3,
        description="Maximum critic review iterations before escalation"
    )

    # Token pricing (per 1M tokens) - Claude 3.5 Sonnet
    input_token_cost_per_million: float = Field(
        default=3.00,
        description="Cost per 1M input tokens"
    )
    output_token_cost_per_million: float = Field(
        default=15.00,
        description="Cost per 1M output tokens"
    )

    # Paths
    workspace_dir: str = Field(
        default="./workspace",
        description="Runtime artifact storage directory"
    )
    library_dir: str = Field(
        default="./librarian/library",
        description="Full Bible texts for RAG indexing"
    )
    cheat_sheets_dir: str = Field(
        default="./librarian/cheat_sheets",
        description="Framework cheat sheets directory"
    )
    output_dir: str = Field(
        default="./outputs",
        description="Final deliverables directory"
    )

    # Critic thresholds
    critic_pass_score: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum score for critic to pass artifact"
    )

    # Router
    router_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for automatic routing; below this asks user"
    )

    # API settings
    anthropic_api_key: str = Field(
        default="",
        description="Anthropic API key (can also use ANTHROPIC_API_KEY env var)"
    )
    api_timeout_seconds: int = Field(
        default=120,
        description="API call timeout in seconds"
    )
    api_max_retries: int = Field(
        default=3,
        description="Maximum retries on API failure"
    )

    # RAGFlow (Forge-Stream Phase 1)
    ragflow_api_url: str = Field(
        default="http://localhost:9380",
        description="RAGFlow API base URL (e.g. http://localhost:9380)",
    )
    ragflow_api_key: str = Field(
        default="",
        description="RAGFlow API key for authentication",
    )
    ragflow_dataset_name: str = Field(
        default="meta-factory-workspace",
        description="Default dataset name for workspace sync",
    )
    ragflow_parse_poll_interval_sec: float = Field(
        default=2.0,
        description="Seconds between polling for document parse status",
    )
    ragflow_parse_timeout_sec: float = Field(
        default=300.0,
        description="Max seconds to wait for document parsing",
    )

    model_config = {
        "env_prefix": "META_FACTORY_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # ignore extra env vars (e.g. OPENAI_API_KEY) not in schema
    }

    def get_workspace_path(self) -> Path:
        """Get workspace path as Path object."""
        return Path(self.workspace_dir)

    def get_output_path(self) -> Path:
        """Get output path as Path object."""
        return Path(self.output_dir)

    def get_cheat_sheets_path(self) -> Path:
        """Get cheat sheets path as Path object."""
        return Path(self.cheat_sheets_dir)

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for given token usage."""
        input_cost = (input_tokens / 1_000_000) * self.input_token_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_token_cost_per_million
        return input_cost + output_cost


# Agent-to-Bible mapping
AGENT_BIBLE_MAPPING: Dict[str, List[str]] = {
    "discovery": ["mom_test.md", "spin_selling.md"],
    "legacy": ["legacy_code_feathers.md", "c4_model.md", "refactoring_fowler.md"],
    "architect": ["eip_hohpe.md", "atam.md"],
    "estimator": ["mcconnell_estimation.md"],
    "proposal": ["minto_pyramid.md", "scqa_framework.md"],
}


# Create singleton instance
settings = Settings()
