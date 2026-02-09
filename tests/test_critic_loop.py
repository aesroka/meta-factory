"""Tests for the Critic Loop functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from agents.critic_agent import CriticAgent
from contracts import (
    CriticVerdict,
    Objection,
    Severity,
    PainMonetizationMatrix,
    PainPoint,
    Frequency,
)


class TestCriticAgent:
    """Test the CriticAgent class."""

    def test_is_duplicate_objection_same_category_similar_description(self):
        """Test duplicate detection for similar objections."""
        critic = CriticAgent("discovery")

        obj1 = Objection(
            category="completeness",
            description="Missing cost quantification for pain points",
            bible_reference="Mom Test",
            severity=Severity.MAJOR,
        )

        obj2 = Objection(
            category="completeness",
            description="Pain points are missing cost quantification",
            bible_reference="Mom Test",
            severity=Severity.MAJOR,
        )

        assert critic._is_duplicate_objection(obj2, [obj1])

    def test_is_duplicate_objection_different_category(self):
        """Test that different categories are not duplicates."""
        critic = CriticAgent("discovery")

        obj1 = Objection(
            category="completeness",
            description="Missing cost data",
            bible_reference="Mom Test",
            severity=Severity.MAJOR,
        )

        obj2 = Objection(
            category="accuracy",
            description="Missing cost data",
            bible_reference="Mom Test",
            severity=Severity.MAJOR,
        )

        assert not critic._is_duplicate_objection(obj2, [obj1])

    def test_similar_descriptions_high_overlap(self):
        """Test similarity detection for high word overlap."""
        critic = CriticAgent("discovery")

        desc1 = "Missing evidence quotes from stakeholders"
        desc2 = "Evidence quotes from stakeholders are missing"

        assert critic._similar_descriptions(desc1, desc2)

    def test_similar_descriptions_low_overlap(self):
        """Test that dissimilar descriptions are not flagged."""
        critic = CriticAgent("discovery")

        desc1 = "Missing cost quantification"
        desc2 = "Stakeholder roles not clearly defined"

        assert not critic._similar_descriptions(desc1, desc2)

    def test_filter_duplicate_objections(self):
        """Test filtering of duplicate objections."""
        critic = CriticAgent("discovery")

        previous = [
            Objection(
                category="completeness",
                description="Missing cost data for pain points in the matrix",
                bible_reference="Mom Test",
                severity=Severity.MAJOR,
            )
        ]

        new_objections = [
            Objection(
                category="completeness",
                # Very similar to previous - high word overlap
                description="Missing cost data for pain points in the output",
                bible_reference="Mom Test",
                severity=Severity.MAJOR,
            ),
            Objection(
                category="accuracy",
                description="Frequency estimates seem unrealistic",  # New
                bible_reference="Mom Test",
                severity=Severity.MINOR,
            ),
        ]

        filtered = critic._filter_duplicate_objections(new_objections, previous)
        assert len(filtered) == 1
        assert filtered[0].category == "accuracy"


class TestCriticVerdict:
    """Test CriticVerdict functionality."""

    def test_has_blocking_objections_true(self):
        """Test detection of blocking objections."""
        verdict = CriticVerdict(
            passed=False,
            score=0.3,
            objections=[
                Objection(
                    category="critical",
                    description="Critical error",
                    bible_reference="Test",
                    severity=Severity.BLOCKING,
                )
            ],
            iteration=0,
            summary="Failed",
        )
        assert verdict.has_blocking_objections()

    def test_has_blocking_objections_false(self):
        """Test when no blocking objections."""
        verdict = CriticVerdict(
            passed=False,
            score=0.5,
            objections=[
                Objection(
                    category="minor",
                    description="Minor issue",
                    bible_reference="Test",
                    severity=Severity.MINOR,
                )
            ],
            iteration=0,
            summary="Needs work",
        )
        assert not verdict.has_blocking_objections()

    def test_has_major_objections(self):
        """Test detection of major objections."""
        verdict = CriticVerdict(
            passed=False,
            score=0.5,
            objections=[
                Objection(
                    category="accuracy",
                    description="Major issue",
                    bible_reference="Test",
                    severity=Severity.MAJOR,
                )
            ],
            iteration=0,
            summary="Needs work",
        )
        assert verdict.has_major_objections()


class TestArtifactValidation:
    """Test that artifacts can be properly created and validated."""

    def test_create_valid_pain_matrix(self):
        """Test creating a valid PainMonetizationMatrix."""
        matrix = PainMonetizationMatrix(
            pain_points=[
                PainPoint(
                    description="Manual data entry",
                    frequency=Frequency.DAILY,
                    cost_per_incident=100.0,
                    annual_cost=26000.0,
                    source_quote="We spend hours on data entry",
                    confidence=0.8,
                )
            ],
            stakeholder_needs=[],
            key_constraints=["Must integrate with legacy ERP"],
            recommended_next_steps=["Automate data entry"],
        )
        assert len(matrix.pain_points) == 1

    def test_pain_matrix_requires_pain_points(self):
        """Test that PainMonetizationMatrix requires at least one pain point."""
        with pytest.raises(ValueError):
            PainMonetizationMatrix(
                pain_points=[],  # Empty - should fail
                stakeholder_needs=[],
            )
