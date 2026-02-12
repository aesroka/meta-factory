"""Critic Agent for reviewing artifacts against Bible frameworks.

The Critic Agent reviews artifacts produced by other agents and validates
them against the relevant Bible frameworks. It uses a circuit breaker pattern
to prevent infinite loops.
"""

import json
from typing import Type, Optional, List, Any
from pydantic import BaseModel

from librarian import Librarian
from providers import get_provider, LLMProvider
from config import settings
from contracts import CriticVerdict, Objection, Severity, HumanEscalation
from agents.base_agent import TokenUsage


class CriticAgent:
    """Reviews artifacts against Bible frameworks.

    Circuit breaker rules:
    1. Max iterations: config.max_critic_iterations (default 3)
    2. Each iteration MUST raise a DIFFERENT objection — no repeats
    3. On max iterations reached: produce HumanEscalation artifact with disagreement log
    4. BLOCKING objections prevent passage. MAJOR objections require fix. MINOR are logged only.
    """

    SYSTEM_PROMPT = """You are a Critical Reviewer Agent for a software consultancy.

Your role is to review artifacts produced by other agents and evaluate them against
established frameworks and best practices.

## Your Responsibilities

1. Evaluate the artifact against the provided framework knowledge
2. Identify any objections where the artifact fails to meet framework standards
3. Score the artifact from 0.0 to 1.0
4. Determine if the artifact passes review (score >= {pass_threshold})

## Severity Levels

- BLOCKING: Critical issues that prevent the artifact from being usable. Must be fixed.
- MAJOR: Significant issues that should be fixed before proceeding.
- MINOR: Small improvements that would enhance quality but aren't essential.

## Review Process

1. Read the artifact carefully
2. Check against each relevant framework principle
3. For each violation, create an objection with:
   - Category (completeness, accuracy, framework_compliance, etc.)
   - Description of the issue
   - Bible/framework reference that is violated
   - Severity level
   - Suggested fix
4. Provide an overall score and pass/fail verdict

## Important Rules

- Be thorough but fair
- Only raise objections for genuine framework violations
- Provide constructive feedback with specific suggestions
- Acknowledge what the artifact does well (list strengths)
- Do NOT repeat objections from previous iterations

## Output Format

Respond with valid JSON matching the CriticVerdict schema.
"""

    def __init__(
        self,
        reviewing_agent_role: str,
        librarian: Optional[Librarian] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """Initialize the Critic Agent.

        Args:
            reviewing_agent_role: The role of the agent being reviewed (e.g., 'discovery')
            librarian: Librarian instance for loading Bible context
            model: Override the default critic model
            provider: Explicit provider name (anthropic, openai, gemini, deepseek)
        """
        self.reviewing_agent_role = reviewing_agent_role
        self.librarian = librarian or Librarian()
        self.bible_context = self.librarian.get_context_for_critic(reviewing_agent_role)

        # Get the LLM provider
        self.llm_provider: LLMProvider = get_provider(provider_name=provider, model=model)
        self.model = model or "tier2"  # Route through Router's tier2 model list (gpt-4o-mini / claude-haiku)
        if hasattr(self.llm_provider, "set_metadata"):
            self.llm_provider.set_metadata({"agent": f"critic({reviewing_agent_role})", "tier": "tier2"})

        self.total_usage = TokenUsage()

    def _build_system_prompt(self) -> str:
        """Build the complete system prompt including Bible context."""
        base_prompt = self.SYSTEM_PROMPT.format(pass_threshold=settings.critic_pass_score)

        parts = [base_prompt]
        parts.append("\n\n# FRAMEWORK KNOWLEDGE\n")
        parts.append("Evaluate the artifact against these frameworks:\n\n")
        parts.append(self.bible_context)
        parts.append("\n\n# OUTPUT SCHEMA\n")
        parts.append(f"```json\n{json.dumps(CriticVerdict.model_json_schema(), indent=2)}\n```")

        return "".join(parts)

    def _build_review_message(
        self,
        artifact: BaseModel,
        iteration: int,
        previous_objections: List[Objection],
    ) -> str:
        """Build the user message for review."""
        parts = [
            f"# ARTIFACT TO REVIEW\n\n",
            f"Type: {type(artifact).__name__}\n\n",
            f"```json\n{artifact.model_dump_json(indent=2)}\n```\n\n",
            f"# REVIEW CONTEXT\n\n",
            f"Iteration: {iteration + 1} of {settings.max_critic_iterations}\n",
        ]

        if previous_objections:
            parts.append("\n# PREVIOUS OBJECTIONS (DO NOT REPEAT)\n\n")
            for i, obj in enumerate(previous_objections, 1):
                parts.append(f"{i}. [{obj.severity.value.upper()}] {obj.category}: {obj.description}\n")

        return "".join(parts)

    def _parse_verdict(self, response_text: str, iteration: int) -> CriticVerdict:
        """Parse and validate critic verdict from response."""
        text = response_text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        data = json.loads(text)

        # Ensure iteration is set correctly
        data["iteration"] = iteration
        data["max_iterations"] = settings.max_critic_iterations
        # Normalize severity to lowercase (LLM may return "MAJOR" etc.)
        for obj in data.get("objections") or []:
            if isinstance(obj.get("severity"), str):
                obj["severity"] = obj["severity"].lower()

        return CriticVerdict.model_validate(data)

    def review(
        self,
        artifact: BaseModel,
        iteration: int = 0,
        previous_objections: Optional[List[Objection]] = None,
    ) -> CriticVerdict:
        """Review an artifact against Bible frameworks.

        Args:
            artifact: The Pydantic model artifact to review
            iteration: Current iteration number (0-indexed)
            previous_objections: Objections from previous iterations (to avoid repeats)

        Returns:
            CriticVerdict with pass/fail, score, and objections
        """
        previous_objections = previous_objections or []

        system_prompt = self._build_system_prompt()
        user_message = self._build_review_message(artifact, iteration, previous_objections)

        response = self.llm_provider.complete(
            system_prompt=system_prompt,
            user_message=user_message,
            model=self.model,
            max_tokens=settings.max_tokens_per_agent_call,
        )

        # Track token usage
        self.total_usage.input_tokens += response.input_tokens
        self.total_usage.output_tokens += response.output_tokens

        verdict = self._parse_verdict(response.content, iteration)

        # Filter out duplicate objections
        verdict.objections = self._filter_duplicate_objections(
            verdict.objections, previous_objections
        )

        # Recalculate passed status based on score threshold
        if verdict.score < settings.critic_pass_score:
            verdict.passed = False

        return verdict

    def _is_duplicate_objection(
        self,
        new_objection: Objection,
        previous_objections: List[Objection],
    ) -> bool:
        """Check if an objection is essentially a repeat of a previous one.

        Prevents the degenerate case of the same complaint looping forever.
        """
        for prev in previous_objections:
            # Check for similar category and description
            if (
                new_objection.category.lower() == prev.category.lower()
                and self._similar_descriptions(new_objection.description, prev.description)
            ):
                return True
        return False

    def _similar_descriptions(self, desc1: str, desc2: str, threshold: float = 0.7) -> bool:
        """Check if two descriptions are similar enough to be considered duplicates.

        Uses simple word overlap for now. Could be enhanced with embeddings.
        """
        words1 = set(desc1.lower().split())
        words2 = set(desc2.lower().split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2

        similarity = len(intersection) / len(union)
        return similarity >= threshold

    def _filter_duplicate_objections(
        self,
        new_objections: List[Objection],
        previous_objections: List[Objection],
    ) -> List[Objection]:
        """Filter out objections that are duplicates of previous ones."""
        filtered = []
        for obj in new_objections:
            if not self._is_duplicate_objection(obj, previous_objections):
                filtered.append(obj)
        return filtered


def run_critic_loop(
    agent_output: BaseModel,
    agent_role: str,
    agent_rerun_fn: callable,
    librarian: Optional[Librarian] = None,
) -> tuple[BaseModel, CriticVerdict, Optional[HumanEscalation]]:
    """Run the critic loop with circuit breaker.

    Args:
        agent_output: Initial output from the agent
        agent_role: Role of the agent (for loading correct Bibles)
        agent_rerun_fn: Function to call to regenerate agent output with feedback
                       Signature: (previous_output, objections) -> new_output
        librarian: Optional Librarian instance

    Returns:
        Tuple of (final_artifact, final_verdict, escalation_or_none)
    """
    critic = CriticAgent(agent_role, librarian=librarian)
    all_objections: List[Objection] = []
    current_output = agent_output

    for iteration in range(settings.max_critic_iterations):
        verdict = critic.review(current_output, iteration, all_objections)

        if verdict.passed:
            return current_output, verdict, None

        # Collect new objections
        all_objections.extend(verdict.objections)

        # Check for blocking objections
        if verdict.has_blocking_objections() or verdict.has_major_objections():
            if iteration < settings.max_critic_iterations - 1:
                # Re-run agent with feedback
                current_output = agent_rerun_fn(current_output, verdict.objections)
            else:
                # Max iterations reached - escalate
                escalation = HumanEscalation(
                    artifact=current_output.model_dump(),
                    review_log=all_objections,
                    reason="Max critic iterations reached with unresolved objections",
                    suggested_resolution="Manual review required to resolve framework compliance issues",
                    context=f"Agent role: {agent_role}, Iterations: {iteration + 1}",
                )
                return current_output, verdict, escalation

    # Final check
    final_verdict = critic.review(current_output, settings.max_critic_iterations - 1, all_objections)
    if not final_verdict.passed:
        escalation = HumanEscalation(
            artifact=current_output.model_dump(),
            review_log=all_objections,
            reason="Max critic iterations reached",
            suggested_resolution="Artifact requires human review",
        )
        return current_output, final_verdict, escalation

    return current_output, final_verdict, None
