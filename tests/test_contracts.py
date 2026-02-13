"""Tests for all Pydantic contracts.

Verifies that every contract can be instantiated with valid data
and that validation works correctly.
"""

import pytest
import math
from datetime import datetime

from contracts import (
    # Router
    InputType,
    Mode,
    InputClassification,
    RoutingDecision,
    # Discovery
    Frequency,
    Priority,
    PainPoint,
    StakeholderNeed,
    PainMonetizationMatrix,
    # Legacy
    SeamType,
    RiskLevel,
    RemediationStrategy,
    C4Level,
    SeamAnalysis,
    TechDebtItem,
    C4Diagram,
    ConstraintList,
    LegacyAnalysisResult,
    # Architecture
    ImportanceLevel,
    DifficultyLevel,
    QualityScenario,
    UtilityTree,
    FailureMode,
    ArchitectureDecision,
    TradeOffMatrix,
    ArchitectureResult,
    # Estimation
    PERTEstimate,
    ConeOfUncertainty,
    ReferenceClass,
    EstimationResult,
    # Critic
    Severity,
    Objection,
    CriticVerdict,
    ReviewLog,
    HumanEscalation,
    # Proposal
    SCQAFrame,
    ExecutiveSummary,
    Milestone,
    RiskItem,
    EngagementSummary,
    ProposalDocument,
)


class TestRouterContracts:
    """Test router-related contracts."""

    def test_input_classification(self):
        classification = InputClassification(
            input_type=InputType.TRANSCRIPT,
            confidence=0.85,
            evidence="Contains meeting dialogue with multiple speakers",
            recommended_mode=Mode.GREENFIELD,
        )
        assert classification.confidence == 0.85
        assert classification.input_type == InputType.TRANSCRIPT

    def test_routing_decision(self):
        decision = RoutingDecision(
            mode=Mode.GREENFIELD,
            swarm_config={"parallel_agents": True},
            bibles_to_load=["mom_test.md", "spin_selling.md"],
        )
        assert decision.mode == Mode.GREENFIELD
        assert len(decision.bibles_to_load) == 2


class TestDiscoveryContracts:
    """Test discovery-related contracts."""

    def test_pain_point(self):
        pain = PainPoint(
            description="Manual data entry takes 4 hours daily",
            frequency=Frequency.DAILY,
            cost_per_incident=200.0,
            annual_cost=52000.0,
            source_quote="We spend half the day just typing stuff into spreadsheets",
            confidence=0.9,
        )
        assert pain.frequency == Frequency.DAILY
        assert pain.confidence == 0.9

    def test_pain_point_validation(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            PainPoint(
                description="Test",
                frequency=Frequency.DAILY,
                source_quote="Test quote",
                confidence=1.5,  # Invalid: > 1.0
            )

    def test_stakeholder_need(self):
        need = StakeholderNeed(
            role="CTO",
            need="Reduce technical debt by 50%",
            priority=Priority.HIGH,
        )
        assert need.role == "CTO"
        assert need.priority == Priority.HIGH

    def test_pain_monetization_matrix(self):
        matrix = PainMonetizationMatrix(
            pain_points=[
                PainPoint(
                    description="Manual reporting",
                    frequency=Frequency.WEEKLY,
                    annual_cost=26000.0,
                    source_quote="Every week we compile reports manually",
                    confidence=0.8,
                )
            ],
            stakeholder_needs=[
                StakeholderNeed(
                    role="Operations Manager",
                    need="Automated reporting",
                    priority=Priority.HIGH,
                )
            ],
            total_annual_cost_of_pain=26000.0,
            key_constraints=["Must integrate with legacy ERP"],
            recommended_next_steps=["Pilot automation with one report type"],
        )
        assert len(matrix.pain_points) == 1
        assert matrix.total_annual_cost_of_pain == 26000.0


class TestLegacyContracts:
    """Test legacy analysis contracts."""

    def test_seam_analysis(self):
        seam = SeamAnalysis(
            seam_type=SeamType.OBJECT,
            location="src/services/PaymentProcessor.java",
            risk_level=RiskLevel.MEDIUM,
            test_strategy="Extract interface, create mock for unit tests",
            description="Payment processor has clear interface boundary",
        )
        assert seam.seam_type == SeamType.OBJECT
        assert seam.risk_level == RiskLevel.MEDIUM

    def test_tech_debt_item(self):
        debt = TechDebtItem(
            module="src/legacy/ReportGenerator.py",
            debt_type="high_coupling",
            cyclomatic_complexity=45,
            coupling_description="Directly accesses 12 database tables",
            remediation_strategy=RemediationStrategy.EXTRACT,
            estimated_effort_hours=16.0,
        )
        assert debt.remediation_strategy == RemediationStrategy.EXTRACT
        assert debt.estimated_effort_hours == 16.0

    def test_c4_diagram(self):
        diagram = C4Diagram(
            level=C4Level.CONTAINER,
            title="Payment System Containers",
            elements=["Web App", "API Server", "Database", "Payment Gateway"],
            relationships=["Web App -> API Server", "API Server -> Database"],
            diagram_code="@startuml\n...\n@enduml",
        )
        assert diagram.level == C4Level.CONTAINER
        assert len(diagram.elements) == 4

    def test_constraint_list(self):
        constraints = ConstraintList(
            hard_constraints=["Cannot modify vendor API integration"],
            soft_constraints=["Prefer Python for new code"],
            no_go_zones=["src/vendor/", "src/legacy/core/"],
        )
        assert len(constraints.no_go_zones) == 2

    def test_legacy_analysis_result(self):
        result = LegacyAnalysisResult(
            seams=[
                SeamAnalysis(
                    seam_type=SeamType.LINK,
                    location="src/api/handlers.py",
                    risk_level=RiskLevel.LOW,
                    test_strategy="Integration tests with mock server",
                    description="API handler layer",
                )
            ],
            tech_debt=[],
            c4_diagrams=[],
            constraints=ConstraintList(),
            summary="Codebase has clear architectural boundaries",
        )
        assert len(result.seams) == 1


class TestArchitectureContracts:
    """Test architecture-related contracts."""

    def test_quality_scenario(self):
        scenario = QualityScenario(
            attribute="performance",
            scenario="System handles 1000 concurrent users",
            importance=ImportanceLevel.HIGH,
            difficulty=DifficultyLevel.MEDIUM,
            stimulus="Peak load during business hours",
            response="Response time < 200ms",
            response_measure="P95 latency measured via APM",
        )
        assert scenario.importance == ImportanceLevel.HIGH

    def test_utility_tree(self):
        tree = UtilityTree(
            scenarios=[
                QualityScenario(
                    attribute="security",
                    scenario="All data encrypted at rest",
                    importance=ImportanceLevel.HIGH,
                    difficulty=DifficultyLevel.LOW,
                ),
                QualityScenario(
                    attribute="scalability",
                    scenario="Scale to 10x current load",
                    importance=ImportanceLevel.HIGH,
                    difficulty=DifficultyLevel.HIGH,
                ),
            ]
        )
        high_priority = tree.get_high_priority_scenarios()
        assert len(high_priority) == 1
        assert high_priority[0].attribute == "scalability"

    def test_architecture_decision(self):
        decision = ArchitectureDecision(
            decision="Use event-driven architecture for order processing",
            context="High volume of orders with complex fulfillment workflow",
            pattern_used="Event Sourcing + CQRS",
            eip_reference="Message Channel, Event Message",
            trade_off="Increased complexity vs. better scalability and auditability",
            alternatives_considered=["Synchronous API calls", "Batch processing"],
            failure_modes=[
                FailureMode(
                    description="Message broker failure",
                    likelihood="rare",
                    impact="severe",
                    mitigation="Multi-zone deployment with failover",
                )
            ],
        )
        assert decision.pattern_used == "Event Sourcing + CQRS"
        assert len(decision.failure_modes) == 1


class TestEstimationContracts:
    """Test estimation-related contracts."""

    def test_pert_estimate(self):
        # O=10, M=15, P=26 -> E=(10+60+26)/6=16, SD=(26-10)/6=2.67
        estimate = PERTEstimate(
            task="Implement user authentication",
            optimistic_hours=10.0,
            likely_hours=15.0,
            pessimistic_hours=26.0,
            expected_hours=16.0,
            std_dev=2.67,
            assumptions=["Using existing OAuth library"],
        )
        assert estimate.expected_hours == 16.0

    def test_pert_estimate_validation(self):
        """Test that PERT math is auto-corrected when LLM returns wrong values."""
        # Wrong expected_hours (20.0) and std_dev; validators correct to (O+4M+P)/6 and (P-O)/6
        estimate = PERTEstimate(
            task="Test",
            optimistic_hours=10.0,
            likely_hours=15.0,
            pessimistic_hours=26.0,
            expected_hours=20.0,  # Wrong: should be 16.0
            std_dev=2.67,
        )
        assert estimate.expected_hours == 16.0  # (10 + 60 + 26) / 6
        assert estimate.std_dev == round((26 - 10) / 6, 2)  # 2.67

    def test_cone_of_uncertainty(self):
        cone = ConeOfUncertainty(
            phase="requirements_complete",
            low_multiplier=0.67,
            high_multiplier=1.5,
            base_estimate=100.0,
            range_low=67.0,
            range_high=150.0,
        )
        assert cone.range_low == 67.0
        assert cone.range_high == 150.0

    def test_reference_class(self):
        ref = ReferenceClass(
            class_name="E-commerce MVP",
            sample_size=15,
            median_hours=480,
            p10_hours=320,
            p90_hours=720,
            similar_projects=["Project A", "Project B"],
        )
        assert ref.sample_size == 15

    def test_estimation_result(self):
        pert1 = PERTEstimate(
            task="Task 1",
            optimistic_hours=8.0,
            likely_hours=12.0,
            pessimistic_hours=20.0,
            expected_hours=12.67,
            std_dev=2.0,
        )
        pert2 = PERTEstimate(
            task="Task 2",
            optimistic_hours=4.0,
            likely_hours=6.0,
            pessimistic_hours=10.0,
            expected_hours=6.33,
            std_dev=1.0,
        )
        total_expected = 12.67 + 6.33  # 19.0
        total_std = math.sqrt(2.0**2 + 1.0**2)  # sqrt(5) ≈ 2.24

        result = EstimationResult(
            pert_estimates=[pert1, pert2],
            cone_of_uncertainty=ConeOfUncertainty(
                phase="initial_concept",
                low_multiplier=0.25,
                high_multiplier=4.0,
                base_estimate=19.0,
                range_low=4.75,
                range_high=76.0,
            ),
            total_expected_hours=total_expected,
            total_std_dev=total_std,
            confidence_interval_90=(14.31, 23.69),
            risk_factors=["New technology stack"],
            caveats=["Estimates assume dedicated team"],
        )
        assert len(result.pert_estimates) == 2


class TestCriticContracts:
    """Test critic-related contracts."""

    def test_objection(self):
        objection = Objection(
            category="framework_compliance",
            description="Pain points lack concrete evidence from past behavior",
            bible_reference="Mom Test - Rule 2: Ask about specifics in the past",
            severity=Severity.MAJOR,
            suggested_fix="Add source quotes from actual incidents",
            artifact_path="pain_points[0].source_quote",
        )
        assert objection.severity == Severity.MAJOR

    def test_critic_verdict_passed(self):
        verdict = CriticVerdict(
            passed=True,
            score=0.85,
            objections=[],
            iteration=1,
            max_iterations=3,
            summary="Artifact meets framework requirements",
            strengths=["Clear pain quantification", "Good stakeholder coverage"],
        )
        assert verdict.passed is True
        assert not verdict.has_blocking_objections()

    def test_critic_verdict_failed(self):
        verdict = CriticVerdict(
            passed=False,
            score=0.45,
            objections=[
                Objection(
                    category="completeness",
                    description="Missing cost quantification",
                    bible_reference="Mom Test",
                    severity=Severity.BLOCKING,
                )
            ],
            iteration=1,
            max_iterations=3,
            summary="Artifact needs revision",
            strengths=[],
        )
        assert verdict.has_blocking_objections()

    def test_human_escalation(self):
        escalation = HumanEscalation(
            artifact={"type": "PainMonetizationMatrix"},
            review_log=[
                Objection(
                    category="accuracy",
                    description="Cost estimates seem unrealistic",
                    bible_reference="McConnell",
                    severity=Severity.MAJOR,
                )
            ],
            reason="Max critic iterations reached",
            suggested_resolution="Verify cost data with stakeholders",
        )
        assert escalation.reason == "Max critic iterations reached"


class TestProposalContracts:
    """Test proposal-related contracts."""

    def test_scqa_frame(self):
        scqa = SCQAFrame(
            situation="Client processes 500 orders daily using manual entry",
            complication="Error rate has reached 15%, costing $50K monthly",
            question="How can we reduce errors while maintaining throughput?",
            answer="Implement automated order processing with validation",
        )
        assert "500 orders" in scqa.situation

    def test_executive_summary(self):
        summary = ExecutiveSummary(
            bottom_line="Automated order processing will save $600K annually",
            key_benefits=[
                "Reduce errors by 90%",
                "Increase throughput by 50%",
                "Free staff for value-add work",
            ],
            investment_summary="$150K implementation + $24K/year maintenance",
            recommended_action="Approve Phase 1 pilot starting Q2",
        )
        assert len(summary.key_benefits) == 3

    def test_milestone(self):
        milestone = Milestone(
            name="Phase 1: MVP",
            description="Core automation for top 3 order types",
            deliverables=["Order intake API", "Validation engine", "Admin dashboard"],
            estimated_hours=240,
            dependencies=[],
        )
        assert milestone.estimated_hours == 240

    def test_proposal_document_to_markdown(self):
        """Test that proposal can be converted to markdown."""
        # Create minimal valid proposal
        pain_point = PainPoint(
            description="Manual entry errors",
            frequency=Frequency.DAILY,
            source_quote="We make mistakes every day",
            confidence=0.9,
        )
        pain_matrix = PainMonetizationMatrix(
            pain_points=[pain_point],
            stakeholder_needs=[],
        )
        scqa = SCQAFrame(
            situation="Current state",
            complication="Problem",
            question="What to do?",
            answer="Solution",
        )
        arch_decision = ArchitectureDecision(
            decision="Use microservices",
            context="Scalability needs",
            pattern_used="Microservices",
            trade_off="Complexity vs scale",
        )
        pert = PERTEstimate(
            task="Implementation",
            optimistic_hours=100,
            likely_hours=150,
            pessimistic_hours=250,
            expected_hours=158.33,
            std_dev=25.0,
        )
        cone = ConeOfUncertainty(
            phase="requirements_complete",
            low_multiplier=0.67,
            high_multiplier=1.5,
            base_estimate=158.33,
            range_low=106.08,
            range_high=237.50,
        )
        engagement = EngagementSummary(
            scqa=scqa,
            pain_matrix=pain_matrix,
            architecture_decisions=[arch_decision],
            estimates=[pert],
            total_estimate=cone,
        )
        executive_summary = ExecutiveSummary(
            bottom_line="We can solve this",
            key_benefits=["Benefit 1", "Benefit 2"],
            investment_summary="$100K",
            recommended_action="Proceed",
        )
        proposal = ProposalDocument(
            title="Test Proposal",
            client_name="Test Client",
            executive_summary=executive_summary,
            engagement_summary=engagement,
            problem_statement="The problem is...",
            proposed_solution="The solution is...",
            technical_approach="We will use...",
            milestones=[
                Milestone(
                    name="Phase 1",
                    description="First phase",
                    deliverables=["Deliverable 1"],
                    estimated_hours=100,
                )
            ],
            timeline_weeks=8,
            investment="$100,000",
        )
        markdown = proposal.to_markdown()
        assert "# Test Proposal" in markdown
        assert "Test Client" in markdown
        assert "Executive Summary" in markdown


def test_all_contracts_import():
    """Verify all contracts can be imported."""
    from contracts import (
        InputType, Mode, InputClassification, RoutingDecision,
        Frequency, Priority, PainPoint, StakeholderNeed, PainMonetizationMatrix,
        SeamType, RiskLevel, RemediationStrategy, C4Level, SeamAnalysis,
        TechDebtItem, C4Diagram, ConstraintList, LegacyAnalysisResult,
        ImportanceLevel, DifficultyLevel, QualityScenario, UtilityTree,
        FailureMode, ArchitectureDecision, TradeOffMatrix, ArchitectureResult,
        PERTEstimate, ConeOfUncertainty, ReferenceClass, EstimationResult,
        Severity, Objection, CriticVerdict, ReviewLog, HumanEscalation,
        SCQAFrame, ExecutiveSummary, Milestone, RiskItem, EngagementSummary,
        ProposalDocument,
    )
    print("All contracts import successfully")
