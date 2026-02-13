"""Tests for contract adapters (Phase 4)."""

import pytest
from contracts import ProjectDossier, Stakeholder, TechConstraint, CoreLogicFlow
from agents import DiscoveryInput
from contracts.adapters import dossier_to_discovery_input, dossier_to_legacy_input


def test_dossier_to_discovery_input_produces_valid_discovery_input():
    """Convert a ProjectDossier with known fields; verify DiscoveryInput transcript contains them."""
    dossier = ProjectDossier(
        project_name="Acme",
        summary="Summary one. Summary two.",
        stakeholders=[
            Stakeholder(name="Alice", role="PM", concerns=["scope", "timeline"]),
            Stakeholder(name="Bob", role="Dev", concerns=[]),
        ],
        tech_stack_detected=["Python", "React", "Postgres"],
        constraints=[
            TechConstraint(category="Security", requirement="SSO", priority="Must-have"),
            TechConstraint(category="DB", requirement="Postgres only", priority="Should-have"),
        ],
        logic_flows=[
            CoreLogicFlow(trigger="User login", process="Auth", outcome="Session"),
        ],
        legacy_debt_summary=None,
    )
    result = dossier_to_discovery_input(dossier)
    assert isinstance(result, DiscoveryInput)
    assert "Acme" in result.transcript
    assert "Summary one" in result.transcript
    assert "Alice" in result.transcript
    assert "Bob" in result.transcript
    assert "PM" in result.transcript
    assert "scope" in result.transcript
    assert "Python" in result.transcript
    assert "React" in result.transcript
    assert "Postgres" in result.transcript
    assert "Security" in result.transcript
    assert "SSO" in result.transcript
    assert "Must-have" in result.transcript
    assert "User login" in result.transcript
    assert "Auth" in result.transcript
    assert "Session" in result.transcript


def test_empty_dossier_produces_minimal_transcript():
    """Dossier with empty lists produces valid transcript (project name + summary only)."""
    dossier = ProjectDossier(
        project_name="Empty",
        summary="No details.",
        stakeholders=[],
        tech_stack_detected=[],
        constraints=[],
        logic_flows=[],
        legacy_debt_summary=None,
    )
    result = dossier_to_discovery_input(dossier)
    assert isinstance(result, DiscoveryInput)
    assert "Empty" in result.transcript
    assert "No details" in result.transcript
    assert "## Stakeholders" not in result.transcript
    assert "## Tech Stack" not in result.transcript
    assert "## Constraints" not in result.transcript
    assert "## Core Flows" not in result.transcript


def test_legacy_debt_included_only_when_present():
    """legacy_debt_summary appears in transcript only when non-null."""
    dossier_none = ProjectDossier(
        project_name="X",
        summary="S.",
        stakeholders=[],
        tech_stack_detected=[],
        constraints=[],
        logic_flows=[],
        legacy_debt_summary=None,
    )
    result_none = dossier_to_discovery_input(dossier_none)
    assert "## Legacy" not in result_none.transcript

    dossier_with = ProjectDossier(
        project_name="Y",
        summary="S.",
        stakeholders=[],
        tech_stack_detected=[],
        constraints=[],
        logic_flows=[],
        legacy_debt_summary="Monolith from 2010.",
    )
    result_with = dossier_to_discovery_input(dossier_with)
    assert "Legacy" in result_with.transcript or "Tech Debt" in result_with.transcript
    assert "Monolith from 2010" in result_with.transcript


def test_dossier_to_legacy_input_produces_codebase_description():
    """dossier_to_legacy_input renders dossier as codebase description for Legacy agent."""
    dossier = ProjectDossier(
        project_name="LegacyApp",
        summary="Legacy system with Java backend.",
        stakeholders=[],
        tech_stack_detected=["Java", "Oracle"],
        constraints=[
            TechConstraint(category="DB", requirement="Oracle only", priority="Must-have"),
        ],
        logic_flows=[],
        legacy_debt_summary="No tests, tight coupling.",
    )
    result = dossier_to_legacy_input(dossier)
    assert isinstance(result, str)
    assert "LegacyApp" in result
    assert "Java" in result
    assert "Oracle" in result
    assert "Legacy / Tech Debt" in result or "legacy_debt" in result.lower() or "No tests" in result
