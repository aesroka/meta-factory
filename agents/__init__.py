"""Agent implementations for Meta-Factory.

Each agent is specialized for a particular task in the consultancy workflow.
"""

from .base_agent import BaseAgent, AgentResult, TokenUsage, AgentInput
from .critic_agent import CriticAgent, run_critic_loop
from .discovery_agent import DiscoveryAgent, DiscoveryInput
from .legacy_agent import LegacyAgent, LegacyInput
from .architect_agent import ArchitectAgent, ArchitectInput
from .estimator_agent import EstimatorAgent, EstimatorInput
from .synthesis_agent import SynthesisAgent, SynthesisInput
from .proposal_agent import ProposalAgent, ProposalInput
from .miner_agent import MinerAgent, MINER_RAG_QUERIES

__all__ = [
    # Base
    "BaseAgent",
    "AgentResult",
    "TokenUsage",
    "AgentInput",
    # Critic
    "CriticAgent",
    "run_critic_loop",
    # Specialized agents
    "DiscoveryAgent",
    "DiscoveryInput",
    "LegacyAgent",
    "LegacyInput",
    "ArchitectAgent",
    "ArchitectInput",
    "EstimatorAgent",
    "EstimatorInput",
    "SynthesisAgent",
    "SynthesisInput",
    "ProposalAgent",
    "ProposalInput",
    "MinerAgent",
    "MINER_RAG_QUERIES",
]
