"""Swarm implementations for Meta-Factory.

Each swarm orchestrates a pipeline of agents for a specific project type.
"""

from .base_swarm import BaseSwarm, SwarmRun
from .greenfield import GreenfieldSwarm, GreenfieldInput
from .brownfield import BrownfieldSwarm, BrownfieldInput
from .greyfield import GreyfieldSwarm, GreyfieldInput
from .ingestion_swarm import IngestionSwarm, IngestionInput

__all__ = [
    "BaseSwarm",
    "SwarmRun",
    "GreenfieldSwarm",
    "GreenfieldInput",
    "BrownfieldSwarm",
    "BrownfieldInput",
    "GreyfieldSwarm",
    "GreyfieldInput",
    "IngestionSwarm",
    "IngestionInput",
]
