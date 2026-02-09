"""Router for directing inputs to the appropriate swarm.

The router uses the classifier to determine the input type and
selects the correct swarm for processing.
"""

from typing import Optional, Union, Dict, Any
from pathlib import Path

from contracts import Mode, RoutingDecision, InputClassification
from router.classifier import InputClassifier, classify_input
from config import settings, AGENT_BIBLE_MAPPING


class Router:
    """Routes inputs to the appropriate swarm based on classification."""

    def __init__(
        self,
        classifier: Optional[InputClassifier] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize the router.

        Args:
            classifier: Optional custom classifier instance
            provider: LLM provider for classification (anthropic, openai, gemini, deepseek)
            model: Model name for classification
        """
        self.classifier = classifier or InputClassifier(provider=provider, model=model)

    def route(
        self,
        input_content: str,
        input_path: Optional[str] = None,
        force_mode: Optional[Mode] = None,
    ) -> RoutingDecision:
        """Determine routing for the given input.

        Args:
            input_content: The input content to route
            input_path: Optional file path for classification hints
            force_mode: Override automatic classification with this mode

        Returns:
            RoutingDecision with mode, config, and bibles to load
        """
        if force_mode:
            # User specified mode
            mode = force_mode
            classification = None
        else:
            # Classify the input
            classification = self.classifier.classify(input_content, input_path)

            # Check confidence threshold
            if classification.confidence < settings.router_confidence_threshold:
                # Low confidence - could prompt user, for now use recommendation
                mode = classification.recommended_mode
            else:
                mode = classification.recommended_mode

        # Build routing decision
        return RoutingDecision(
            mode=mode,
            swarm_config=self._get_swarm_config(mode, classification),
            bibles_to_load=self._get_bibles_for_mode(mode),
        )

    def _get_swarm_config(
        self,
        mode: Mode,
        classification: Optional[InputClassification] = None,
    ) -> Dict[str, Any]:
        """Get configuration for the selected swarm."""
        config = {
            "mode": mode.value,
        }

        if classification:
            config["classification"] = {
                "input_type": classification.input_type.value,
                "confidence": classification.confidence,
                "evidence": classification.evidence,
            }

        # Mode-specific configuration
        if mode == Mode.GREENFIELD:
            config["stages"] = [
                "discovery", "architecture", "estimation", "synthesis", "proposal"
            ]
        elif mode == Mode.BROWNFIELD:
            config["stages"] = [
                "legacy_analysis", "refactoring_plan", "estimation", "synthesis", "proposal"
            ]
        elif mode == Mode.GREYFIELD:
            config["stages"] = [
                "parallel_analysis", "constraint_reconciliation",
                "architecture", "estimation", "synthesis", "proposal"
            ]
            config["parallel_stages"] = ["discovery", "legacy_analysis"]

        return config

    def _get_bibles_for_mode(self, mode: Mode) -> list[str]:
        """Get the list of bibles needed for the given mode."""
        if mode == Mode.GREENFIELD:
            return (
                AGENT_BIBLE_MAPPING["discovery"] +
                AGENT_BIBLE_MAPPING["architect"] +
                AGENT_BIBLE_MAPPING["estimator"] +
                AGENT_BIBLE_MAPPING["proposal"]
            )
        elif mode == Mode.BROWNFIELD:
            return (
                AGENT_BIBLE_MAPPING["legacy"] +
                AGENT_BIBLE_MAPPING["architect"] +
                AGENT_BIBLE_MAPPING["estimator"] +
                AGENT_BIBLE_MAPPING["proposal"]
            )
        elif mode == Mode.GREYFIELD:
            # All bibles for hybrid mode
            all_bibles = []
            for bibles in AGENT_BIBLE_MAPPING.values():
                all_bibles.extend(bibles)
            return list(set(all_bibles))

        return []


def route_input(
    content: str,
    path: Optional[str] = None,
    force_mode: Optional[Mode] = None,
) -> RoutingDecision:
    """Convenience function for routing input.

    Args:
        content: Input content to route
        path: Optional file path for hints
        force_mode: Override automatic classification

    Returns:
        RoutingDecision with mode and configuration
    """
    router = Router()
    return router.route(content, path, force_mode)
