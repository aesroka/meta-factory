"""Input classifier for determining project type and routing mode.

Uses heuristic pre-filtering combined with LLM confidence scoring
to classify inputs and recommend the appropriate swarm.
"""

import os
import json
from pathlib import Path
from typing import Optional, Tuple

from contracts import InputType, Mode, InputClassification
from providers import get_provider
from config import settings


class InputClassifier:
    """Classifies input to determine appropriate processing mode.

    Uses a two-stage approach:
    1. Heuristic pre-filter for obvious cases
    2. LLM confidence scoring for ambiguous cases
    """

    # Heuristic patterns for quick classification
    CODE_INDICATORS = [
        ".py", ".js", ".ts", ".java", ".go", ".rs", ".rb", ".php",
        ".cs", ".cpp", ".c", ".h", ".swift", ".kt",
        "def ", "function ", "class ", "import ", "from ", "require(",
        "package ", "public ", "private ", "async ", "await ",
    ]

    TRANSCRIPT_INDICATORS = [
        "meeting", "call", "transcript", "conversation",
        "speaker", "attendee", "minutes",
        "said", "mentioned", "discussed", "agreed",
        "Q:", "A:", "[", "]:",  # Speaker labels
    ]

    IDEA_INDICATORS = [
        "idea", "concept", "proposal", "brief",
        "we want to", "we need to", "we should",
        "the goal is", "objective", "requirement",
    ]

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        """Initialize the classifier.

        Args:
            model: Override the default model for classification
            provider: Explicit provider name
        """
        self.llm_provider = get_provider(provider_name=provider, model=model)
        self.model = model or self.llm_provider.default_model
        self.llm_available = self.llm_provider.is_available()

    def classify(self, input_content: str, input_path: Optional[str] = None) -> InputClassification:
        """Classify the input content.

        Args:
            input_content: The text content to classify
            input_path: Optional path for file-based heuristics

        Returns:
            InputClassification with type, confidence, and recommended mode
        """
        # Stage 1: Heuristic pre-filter
        heuristic_result = self._heuristic_classify(input_content, input_path)
        input_type, confidence, evidence = heuristic_result

        # If high confidence from heuristics, use it
        if confidence >= 0.8:
            return InputClassification(
                input_type=input_type,
                confidence=confidence,
                evidence=evidence,
                recommended_mode=self._type_to_mode(input_type),
            )

        # Stage 2: Try LLM classification for ambiguous cases (if API key available)
        if self.api_key:
            try:
                return self._llm_classify(input_content, input_path)
            except Exception as e:
                # Fall back to heuristics if LLM fails
                pass

        # Fall back to heuristics with lower confidence
        return InputClassification(
            input_type=input_type,
            confidence=confidence,
            evidence=f"{evidence} (heuristic only)",
            recommended_mode=self._type_to_mode(input_type),
        )

    def _heuristic_classify(
        self,
        content: str,
        path: Optional[str] = None,
    ) -> Tuple[InputType, float, str]:
        """Apply heuristic rules for quick classification.

        Returns:
            Tuple of (InputType, confidence, evidence)
        """
        content_lower = content.lower()
        evidence_parts = []

        # Check for code indicators
        code_score = 0
        for indicator in self.CODE_INDICATORS:
            if indicator in content or indicator in content_lower:
                code_score += 1
                if len(evidence_parts) < 3:
                    evidence_parts.append(f"Contains '{indicator}'")

        # Check for transcript indicators
        transcript_score = 0
        for indicator in self.TRANSCRIPT_INDICATORS:
            if indicator in content_lower:
                transcript_score += 1
                if len(evidence_parts) < 3:
                    evidence_parts.append(f"Contains '{indicator}'")

        # Check for idea indicators
        idea_score = 0
        for indicator in self.IDEA_INDICATORS:
            if indicator in content_lower:
                idea_score += 1
                if len(evidence_parts) < 3:
                    evidence_parts.append(f"Contains '{indicator}'")

        # Check path for additional hints
        if path:
            path_lower = path.lower()
            if any(ext in path_lower for ext in [".py", ".js", ".ts", ".java"]):
                code_score += 5
                evidence_parts.append("File extension indicates code")
            elif any(word in path_lower for word in ["transcript", "meeting", "call"]):
                transcript_score += 5
                evidence_parts.append("Filename suggests transcript")

        # Determine winner
        scores = {
            InputType.CODE_BASE: code_score,
            InputType.TRANSCRIPT: transcript_score,
            InputType.IDEA: idea_score,
        }

        max_type = max(scores, key=scores.get)
        max_score = scores[max_type]
        total_score = sum(scores.values()) or 1

        # Calculate confidence
        if max_score == 0:
            return InputType.IDEA, 0.3, "No strong indicators found"

        confidence = min(0.9, max_score / (total_score + 3))  # Dampen confidence

        # Check for hybrid
        if code_score > 0 and transcript_score > 0:
            return InputType.HYBRID, confidence * 0.8, "; ".join(evidence_parts)

        return max_type, confidence, "; ".join(evidence_parts) or "Heuristic analysis"

    def _llm_classify(
        self,
        content: str,
        path: Optional[str] = None,
    ) -> InputClassification:
        """Use LLM for classification when heuristics are uncertain."""
        system_prompt = """You are an input classifier for a software consultancy system.

Classify the input into one of these types:
- CODE_BASE: Programming code, file structures, technical implementations
- TRANSCRIPT: Meeting transcripts, call recordings, interview notes
- IDEA: Project briefs, requirements, feature requests, conceptual descriptions
- HYBRID: Mix of code and business context (e.g., codebase + requirements)

For each classification, also recommend a processing mode:
- GREENFIELD: For new projects starting from scratch (transcripts, ideas)
- BROWNFIELD: For legacy codebase modernization (code bases)
- GREYFIELD: For existing platforms with new requirements (hybrid)

Respond with JSON matching this schema:
{
    "input_type": "CODE_BASE" | "TRANSCRIPT" | "IDEA" | "HYBRID",
    "confidence": 0.0-1.0,
    "evidence": "Brief explanation of classification",
    "recommended_mode": "GREENFIELD" | "BROWNFIELD" | "GREYFIELD"
}"""

        # Truncate content if too long
        max_content_length = 4000
        if len(content) > max_content_length:
            truncated_content = content[:max_content_length] + "\n...[truncated]..."
        else:
            truncated_content = content

        user_message = f"Classify this input:\n\n{truncated_content}"
        if path:
            user_message = f"File path: {path}\n\n{user_message}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse response
        text = response.content[0].text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        data = json.loads(text)

        return InputClassification(
            input_type=InputType(data["input_type"].lower()),
            confidence=data["confidence"],
            evidence=data["evidence"],
            recommended_mode=Mode(data["recommended_mode"].lower()),
        )

    def _type_to_mode(self, input_type: InputType) -> Mode:
        """Map input type to recommended processing mode."""
        mapping = {
            InputType.CODE_BASE: Mode.BROWNFIELD,
            InputType.TRANSCRIPT: Mode.GREENFIELD,
            InputType.IDEA: Mode.GREENFIELD,
            InputType.HYBRID: Mode.GREYFIELD,
        }
        return mapping.get(input_type, Mode.GREENFIELD)


def classify_input(content: str, path: Optional[str] = None) -> InputClassification:
    """Convenience function for classifying input.

    Args:
        content: Input content to classify
        path: Optional file path for hints

    Returns:
        InputClassification result
    """
    classifier = InputClassifier()
    return classifier.classify(content, path)
