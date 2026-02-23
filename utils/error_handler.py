"""Friendly error handling for CLI (Phase 15)."""

import traceback
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    _console = Console()
except ImportError:
    _console = None


def handle_error(error: Exception, context: Optional[dict] = None) -> None:
    """Display user-friendly error with suggestions."""
    err_str = str(error)
    if _console is None:
        print(f"Error: {err_str}")
        traceback.print_exc()
        return

    if "No LLM providers configured" in err_str or "No LLM provider" in err_str:
        _console.print(Panel(
            "[red]No LLM provider configured[/red]\n\n"
            "Set at least one API key:\n\n"
            "  export OPENAI_API_KEY=sk-...\n\n"
            "Or add to .env: OPENAI_API_KEY=sk-...\n\n"
            "See README.md for setup.",
            title="Setup Error",
            border_style="red",
        ))
        return

    if "401" in err_str or "Unauthorized" in err_str or "invalid_api_key" in err_str.lower():
        _console.print(Panel(
            "[red]API key invalid or rejected[/red]\n\n"
            "Check: key is correct, not expired, and has credits.\n\n"
            f"[dim]{err_str}[/dim]",
            title="Authentication Error",
            border_style="red",
        ))
        return

    if "Budget exceeded" in err_str or "max_budget" in err_str or "cost limit" in err_str.lower():
        _console.print(Panel(
            "[red]Cost limit exceeded[/red]\n\n"
            "Increase --max-cost or reduce input/quality.\n\n"
            f"[dim]{err_str}[/dim]",
            title="Budget Exceeded",
            border_style="red",
        ))
        return

    _console.print(Panel(
        f"[red]{err_str}[/red]\n\n[dim]{traceback.format_exc()}[/dim]",
        title="Error",
        border_style="red",
    ))
