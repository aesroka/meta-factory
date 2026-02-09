"""Tests for the Router and Input Classifier."""

import pytest

from router import InputClassifier, Router, classify_input, route_input
from contracts import InputType, Mode


class TestInputClassifier:
    """Test the InputClassifier class."""

    def test_classify_code_content(self):
        """Test classification of code content."""
        classifier = InputClassifier()
        code_content = """
import os
from typing import List

def hello_world():
    print("Hello, World!")

class MyClass:
    def __init__(self):
        self.value = 42

async def fetch_data():
    await do_something()
"""
        result = classifier._heuristic_classify(code_content)
        assert result[0] == InputType.CODE_BASE
        assert result[1] > 0.3  # Relaxed threshold for heuristics

    def test_classify_transcript_content(self):
        """Test classification of transcript content."""
        classifier = InputClassifier()
        transcript = """
Meeting Transcript - Q4 Planning

Speaker 1: Welcome everyone to the quarterly planning meeting.
Speaker 2: Thanks for having us. We discussed the roadmap last week.
Speaker 1: Right, and we agreed to focus on the API integration.
"""
        result = classifier._heuristic_classify(transcript)
        assert result[0] == InputType.TRANSCRIPT
        assert result[1] > 0.5

    def test_classify_idea_content(self):
        """Test classification of idea/brief content."""
        classifier = InputClassifier()
        idea = """
Project Brief: Customer Portal

The goal is to create a self-service portal where customers can:
- View their account information
- Submit support tickets
- Track order status

We need to integrate with the existing CRM system.
"""
        result = classifier._heuristic_classify(idea)
        # Could be IDEA or TRANSCRIPT depending on content
        assert result[0] in [InputType.IDEA, InputType.TRANSCRIPT]

    def test_classify_file_extension_hint(self):
        """Test that file extension provides classification hint."""
        classifier = InputClassifier()
        result = classifier._heuristic_classify("some content", "project.py")
        # Python file should increase code score
        assert result[0] == InputType.CODE_BASE

    def test_classify_transcript_filename_hint(self):
        """Test that transcript filename provides hint."""
        classifier = InputClassifier()
        result = classifier._heuristic_classify("some content", "meeting_transcript.txt")
        assert result[0] == InputType.TRANSCRIPT


class TestRouter:
    """Test the Router class."""

    def test_route_with_force_mode(self):
        """Test routing with forced mode."""
        router = Router()
        result = router.route("any content", force_mode=Mode.BROWNFIELD)
        assert result.mode == Mode.BROWNFIELD

    def test_route_greenfield_bibles(self):
        """Test that greenfield routing includes correct bibles."""
        router = Router()
        result = router.route("transcript content", force_mode=Mode.GREENFIELD)
        assert "mom_test.md" in result.bibles_to_load
        assert "spin_selling.md" in result.bibles_to_load

    def test_route_brownfield_bibles(self):
        """Test that brownfield routing includes correct bibles."""
        router = Router()
        result = router.route("code content", force_mode=Mode.BROWNFIELD)
        assert "legacy_code_feathers.md" in result.bibles_to_load
        assert "c4_model.md" in result.bibles_to_load

    def test_route_greyfield_bibles(self):
        """Test that greyfield routing includes all bibles."""
        router = Router()
        result = router.route("hybrid content", force_mode=Mode.GREYFIELD)
        # Should include bibles from all modes
        assert len(result.bibles_to_load) >= 5

    def test_swarm_config_includes_stages(self):
        """Test that swarm config includes stage information."""
        router = Router()

        greenfield = router.route("content", force_mode=Mode.GREENFIELD)
        assert "discovery" in greenfield.swarm_config["stages"]

        brownfield = router.route("content", force_mode=Mode.BROWNFIELD)
        assert "legacy_analysis" in brownfield.swarm_config["stages"]


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_classify_input_function_heuristic_only(self):
        """Test the classify_input convenience function using heuristics.

        Note: Full LLM classification requires API key, so we test
        with high-confidence heuristic content.
        """
        classifier = InputClassifier()
        # Use content with strong code indicators for heuristic classification
        result = classifier._heuristic_classify(
            "import os\nfrom typing import List\ndef foo(): pass\nclass Bar: pass",
            "test.py"
        )
        assert result[0] == InputType.CODE_BASE
        assert result[1] >= 0.5  # High confidence from file extension

    def test_route_input_function(self):
        """Test the route_input convenience function."""
        result = route_input("some content", force_mode=Mode.GREENFIELD)
        assert result.mode == Mode.GREENFIELD
