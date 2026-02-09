"""Tests for the Librarian module."""

import pytest
from pathlib import Path

from librarian import Librarian, get_librarian
from config import AGENT_BIBLE_MAPPING


class TestLibrarian:
    """Test the Librarian class."""

    def test_init_loads_cheat_sheets(self):
        """Test that librarian loads cheat sheets on init."""
        lib = Librarian()
        sheets = lib.list_available_cheat_sheets()
        assert len(sheets) > 0
        assert "mom_test.md" in sheets
        assert "spin_selling.md" in sheets

    def test_get_cheat_sheet(self):
        """Test getting a single cheat sheet."""
        lib = Librarian()
        content = lib.get_cheat_sheet("mom_test.md")
        assert "Mom Test" in content
        assert "People lie to be polite" in content

    def test_get_cheat_sheet_not_found(self):
        """Test that missing cheat sheet raises KeyError."""
        lib = Librarian()
        with pytest.raises(KeyError):
            lib.get_cheat_sheet("nonexistent.md")

    def test_get_context_for_discovery_agent(self):
        """Test context loading for discovery agent."""
        lib = Librarian()
        context = lib.get_context_for_agent("discovery")
        # Should include Mom Test and SPIN Selling
        assert "Mom Test" in context
        assert "SPIN" in context

    def test_get_context_for_legacy_agent(self):
        """Test context loading for legacy agent."""
        lib = Librarian()
        context = lib.get_context_for_agent("legacy")
        # Should include Feathers, C4, and Fowler
        assert "Legacy Code" in context or "Feathers" in context
        assert "C4" in context
        assert "Refactoring" in context

    def test_get_context_for_architect_agent(self):
        """Test context loading for architect agent."""
        lib = Librarian()
        context = lib.get_context_for_agent("architect")
        # Should include EIP and ATAM
        assert "Enterprise Integration" in context or "EIP" in context
        assert "ATAM" in context

    def test_get_context_for_estimator_agent(self):
        """Test context loading for estimator agent."""
        lib = Librarian()
        context = lib.get_context_for_agent("estimator")
        # Should include McConnell
        assert "PERT" in context or "McConnell" in context
        assert "Cone of Uncertainty" in context

    def test_get_context_for_proposal_agent(self):
        """Test context loading for proposal agent."""
        lib = Librarian()
        context = lib.get_context_for_agent("proposal")
        # Should include Minto and SCQA
        assert "Minto" in context or "Pyramid" in context
        assert "SCQA" in context

    def test_get_context_unknown_role(self):
        """Test that unknown role raises ValueError."""
        lib = Librarian()
        with pytest.raises(ValueError):
            lib.get_context_for_agent("unknown_role")

    def test_get_context_for_critic(self):
        """Test that critic gets same context as agent being reviewed."""
        lib = Librarian()
        agent_context = lib.get_context_for_agent("discovery")
        critic_context = lib.get_context_for_critic("discovery")
        assert agent_context == critic_context

    def test_case_insensitive_role(self):
        """Test that role lookup is case insensitive."""
        lib = Librarian()
        lower = lib.get_context_for_agent("discovery")
        upper = lib.get_context_for_agent("DISCOVERY")
        mixed = lib.get_context_for_agent("Discovery")
        assert lower == upper == mixed

    def test_all_configured_roles_have_cheat_sheets(self):
        """Test that all roles in config have valid cheat sheets."""
        lib = Librarian()
        available = lib.list_available_cheat_sheets()

        for role, bibles in AGENT_BIBLE_MAPPING.items():
            for bible in bibles:
                assert bible in available, f"Missing cheat sheet: {bible} for role {role}"

    def test_get_all_context(self):
        """Test getting all cheat sheets combined."""
        lib = Librarian()
        all_context = lib.get_all_context()
        # Should include content from all cheat sheets
        assert "Mom Test" in all_context
        assert "ATAM" in all_context
        assert "C4" in all_context

    def test_rag_not_implemented(self):
        """Test that RAG methods raise NotImplementedError."""
        lib = Librarian()
        with pytest.raises(NotImplementedError):
            lib.get_rag_passages("test query", "discovery")


class TestLibrarianSingleton:
    """Test the singleton accessor."""

    def test_get_librarian_returns_same_instance(self):
        """Test that get_librarian returns singleton."""
        lib1 = get_librarian()
        lib2 = get_librarian()
        assert lib1 is lib2

    def test_get_librarian_is_functional(self):
        """Test that singleton librarian works."""
        lib = get_librarian()
        context = lib.get_context_for_agent("discovery")
        assert len(context) > 0


class TestCheatSheetContent:
    """Test that cheat sheets have expected content."""

    @pytest.fixture
    def librarian(self):
        return Librarian()

    def test_mom_test_has_key_concepts(self, librarian):
        """Test Mom Test cheat sheet has key concepts."""
        content = librarian.get_cheat_sheet("mom_test.md")
        assert "Pain" in content
        assert "past" in content.lower() or "behavior" in content.lower()
        assert "hypothetical" in content.lower() or "forbidden" in content.lower()

    def test_spin_has_question_types(self, librarian):
        """Test SPIN cheat sheet has all question types."""
        content = librarian.get_cheat_sheet("spin_selling.md")
        assert "Situation" in content
        assert "Problem" in content
        assert "Implication" in content
        assert "Need-Payoff" in content or "Need Payoff" in content

    def test_pert_has_formulas(self, librarian):
        """Test McConnell cheat sheet has PERT formulas."""
        content = librarian.get_cheat_sheet("mcconnell_estimation.md")
        assert "Optimistic" in content
        assert "Pessimistic" in content
        assert "Expected" in content

    def test_c4_has_all_levels(self, librarian):
        """Test C4 cheat sheet has all diagram levels."""
        content = librarian.get_cheat_sheet("c4_model.md")
        assert "Context" in content
        assert "Container" in content
        assert "Component" in content
        assert "Code" in content

    def test_minto_has_pyramid_structure(self, librarian):
        """Test Minto cheat sheet explains pyramid structure."""
        content = librarian.get_cheat_sheet("minto_pyramid.md")
        assert "BLUF" in content or "Bottom Line" in content
        assert "SCQA" in content or "pyramid" in content.lower()
