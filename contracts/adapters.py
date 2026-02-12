"""Adapters between contracts (Phase 4).

Pure functions to convert one contract type to another for pipeline handoffs.
"""

from contracts import ProjectDossier
from agents import DiscoveryInput


def dossier_to_discovery_input(dossier: ProjectDossier) -> DiscoveryInput:
    """Format a ProjectDossier as a structured transcript for Discovery.

    Discovery expects a DiscoveryInput with a `transcript` string.
    We render the Dossier's structured fields as a readable document
    so Discovery can analyze it for pain points, monetization, etc.
    """
    sections = [f"# Project: {dossier.project_name}\n\n{dossier.summary}"]

    if dossier.stakeholders:
        lines = ["## Stakeholders"]
        for s in dossier.stakeholders:
            concerns = ", ".join(s.concerns) if s.concerns else "none stated"
            lines.append(f"- **{s.name}** ({s.role}): {concerns}")
        sections.append("\n".join(lines))

    if dossier.tech_stack_detected:
        sections.append("## Tech Stack\n" + ", ".join(dossier.tech_stack_detected))

    if dossier.constraints:
        lines = ["## Constraints"]
        for c in dossier.constraints:
            lines.append(f"- [{c.priority}] {c.category}: {c.requirement}")
        sections.append("\n".join(lines))

    if dossier.logic_flows:
        lines = ["## Core Flows"]
        for f in dossier.logic_flows:
            lines.append(f"- **Trigger:** {f.trigger} → **Process:** {f.process} → **Outcome:** {f.outcome}")
        sections.append("\n".join(lines))

    if dossier.legacy_debt_summary:
        sections.append(f"## Legacy / Tech Debt\n{dossier.legacy_debt_summary}")

    return DiscoveryInput(transcript="\n\n".join(sections))
