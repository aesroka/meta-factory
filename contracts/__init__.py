"""Pydantic contracts for the Meta-Factory system.

All agent-to-agent handoffs are typed through these contracts.
"""

from .router_contracts import (
    InputType,
    Mode,
    InputClassification,
    RoutingDecision,
)

from .discovery_contracts import (
    Frequency,
    Priority,
    PainPoint,
    StakeholderNeed,
    PainMonetizationMatrix,
)

from .legacy_contracts import (
    SeamType,
    RiskLevel,
    RemediationStrategy,
    C4Level,
    SeamAnalysis,
    TechDebtItem,
    C4Diagram,
    ConstraintList,
    LegacyAnalysisResult,
)

from .architecture_contracts import (
    ImportanceLevel,
    DifficultyLevel,
    QualityScenario,
    UtilityTree,
    FailureMode,
    ArchitectureDecision,
    TradeOffMatrix,
    ArchitectureResult,
)

from .estimation_contracts import (
    PERTEstimate,
    ConeOfUncertainty,
    ReferenceClass,
    EstimationResult,
)

from .critic_contracts import (
    Severity,
    Objection,
    CriticVerdict,
    ReviewLog,
    HumanEscalation,
)

from .proposal_contracts import (
    SCQAFrame,
    ExecutiveSummary,
    Milestone,
    RiskItem,
    EngagementSummary,
    ProposalDocument,
)

from .project import (
    MinerInput,
    Stakeholder,
    TechConstraint,
    CoreLogicFlow,
    ProjectDossier,
)

from .reconciliation import DossierReconciliation

__all__ = [
    # Router
    "InputType",
    "Mode",
    "InputClassification",
    "RoutingDecision",
    # Discovery
    "Frequency",
    "Priority",
    "PainPoint",
    "StakeholderNeed",
    "PainMonetizationMatrix",
    # Legacy
    "SeamType",
    "RiskLevel",
    "RemediationStrategy",
    "C4Level",
    "SeamAnalysis",
    "TechDebtItem",
    "C4Diagram",
    "ConstraintList",
    "LegacyAnalysisResult",
    # Architecture
    "ImportanceLevel",
    "DifficultyLevel",
    "QualityScenario",
    "UtilityTree",
    "FailureMode",
    "ArchitectureDecision",
    "TradeOffMatrix",
    "ArchitectureResult",
    # Estimation
    "PERTEstimate",
    "ConeOfUncertainty",
    "ReferenceClass",
    "EstimationResult",
    # Critic
    "Severity",
    "Objection",
    "CriticVerdict",
    "ReviewLog",
    "HumanEscalation",
    # Proposal
    "SCQAFrame",
    "ExecutiveSummary",
    "Milestone",
    "RiskItem",
    "EngagementSummary",
    "ProposalDocument",
    # Project (Forge-Stream Dossier)
    "MinerInput",
    "Stakeholder",
    "TechConstraint",
    "CoreLogicFlow",
    "ProjectDossier",
    # Reconciliation (Phase 6)
    "DossierReconciliation",
]
