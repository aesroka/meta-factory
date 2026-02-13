#!/usr/bin/env python3
"""Meta-Factory CLI - Entry point for the autonomous proposal system.

Usage:
    # Auto-detect mode from input
    python main.py --input ./transcript.txt --client "Acme Corp"

    # Force a specific mode
    python main.py --input ./legacy_code/ --client "Acme Corp" --mode brownfield

    # Greyfield with both inputs
    python main.py --input ./transcript.txt --codebase ./legacy_code/ --client "Acme Corp" --mode greyfield
"""

import sys
import json
from pathlib import Path
from typing import Optional

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Missing dependencies. Run: pip install click rich")
    sys.exit(1)

from contracts import Mode
from orchestrator import EngagementManager, run_factory
from router import classify_input
from providers import list_providers as get_available_providers
from config import settings


console = Console()


def read_input_content(input_path: str) -> str:
    """Read input content from file or directory.

    Args:
        input_path: Path to file or directory

    Returns:
        Content as string
    """
    path = Path(input_path)

    if not path.exists():
        # Treat as literal content
        return input_path

    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")

    if path.is_dir():
        # Concatenate all text files in directory
        content_parts = []
        for file in sorted(path.rglob("*")):
            if file.is_file() and file.suffix in [
                ".txt", ".md", ".py", ".js", ".ts", ".java", ".go",
                ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h"
            ]:
                try:
                    content_parts.append(f"=== {file.name} ===\n")
                    content_parts.append(file.read_text(encoding="utf-8", errors="replace"))
                    content_parts.append("\n\n")
                except Exception:
                    pass
        return "".join(content_parts)

    return input_path


@click.command()
@click.option(
    "--input", "-i", "input_path",
    required=False,
    help="Path to input file/directory or literal input text"
)
@click.option(
    "--client", "-c", "client_name",
    required=False,
    help="Client name for the proposal"
)
@click.option(
    "--codebase", "-b",
    help="Path to codebase for greyfield mode"
)
@click.option(
    "--mode", "-m",
    type=click.Choice(["auto", "greenfield", "brownfield", "greyfield"]),
    default="auto",
    help="Processing mode (default: auto-detect)"
)
@click.option(
    "--max-cost", "-$",
    type=float,
    default=None,
    help=f"Maximum cost in USD (default: ${settings.max_cost_per_run_usd})"
)
@click.option(
    "--output", "-o", "output_dir",
    default=None,
    help="Output directory (default: ./outputs)"
)
@click.option(
    "--provider", "-p",
    type=click.Choice(["anthropic", "openai", "gemini", "deepseek"]),
    default=None,
    help="LLM provider (default: anthropic)"
)
@click.option(
    "--model",
    default=None,
    help="Model name (e.g., gpt-4o, gemini-pro, deepseek-chat)"
)
@click.option(
    "--classify-only",
    is_flag=True,
    help="Only classify input, don't run full pipeline"
)
@click.option(
    "--list-providers",
    is_flag=True,
    help="List available providers and exit"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Verbose output"
)
@click.option(
    "--quality",
    type=click.Choice(["standard", "premium"]),
    default="standard",
    help="standard = RAG-only, single estimator; premium = hybrid context, ensemble estimation"
)
@click.option(
    "--hourly-rate",
    type=float,
    default=150,
    help="Hourly rate in GBP for cost estimates (default: 150)"
)
def main(
    input_path: str,
    client_name: str,
    codebase: Optional[str],
    mode: str,
    max_cost: Optional[float],
    output_dir: Optional[str],
    provider: Optional[str],
    model: Optional[str],
    classify_only: bool,
    list_providers: bool,
    verbose: bool,
    quality: str,
    hourly_rate: float,
):
    """Meta-Factory: Autonomous AI Proposal System.

    Ingests diverse inputs (transcripts, ideas, codebases) and orchestrates
    specialized agent swarms to produce production-ready software proposals.
    """
    # Handle --list-providers
    if list_providers:
        console.print("[bold]Available LLM Providers:[/bold]\n")
        providers_status = get_available_providers()
        for name, available in providers_status.items():
            status = "[green]✓ Ready[/green]" if available else "[red]✗ No API key[/red]"
            console.print(f"  {name:12} {status}")
        console.print("\n[dim]Set API keys via environment variables:[/dim]")
        console.print("  ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, DEEPSEEK_API_KEY")
        return

    # Validate required options
    if not input_path:
        console.print("[red]Error: --input is required[/red]")
        sys.exit(1)
    if not client_name:
        console.print("[red]Error: --client is required[/red]")
        sys.exit(1)

    console.print(Panel.fit(
        "[bold blue]Meta-Factory[/bold blue]\n"
        "[dim]Autonomous AI Proposal System[/dim]",
        border_style="blue"
    ))

    # Show provider info
    if provider or model:
        console.print(f"\n[dim]Provider:[/dim] {provider or 'auto-detect'}")
        if model:
            console.print(f"[dim]Model:[/dim] {model}")

    # Read input content
    console.print(f"\n[dim]Reading input from:[/dim] {input_path}")
    input_content = read_input_content(input_path)

    if not input_content.strip():
        console.print("[red]Error: Input content is empty[/red]")
        sys.exit(1)

    console.print(f"[dim]Input size:[/dim] {len(input_content):,} characters")

    # Classify input if in auto mode
    if mode == "auto" or classify_only:
        console.print("\n[bold]Classifying input...[/bold]")
        classification = classify_input(
            input_content, input_path, provider=provider, model=model
        )

        console.print(f"  [green]Type:[/green] {classification.input_type.value}")
        console.print(f"  [green]Confidence:[/green] {classification.confidence:.0%}")
        console.print(f"  [green]Evidence:[/green] {classification.evidence}")
        console.print(f"  [green]Recommended mode:[/green] {classification.recommended_mode.value}")

        if classify_only:
            return

    # Determine mode
    if mode == "auto":
        force_mode = None
    else:
        force_mode = Mode(mode)

    # Read codebase if provided
    codebase_content = None
    if codebase:
        console.print(f"\n[dim]Reading codebase from:[/dim] {codebase}")
        codebase_content = read_input_content(codebase)
        console.print(f"[dim]Codebase size:[/dim] {len(codebase_content):,} characters")

    # Check for greyfield mode requirements
    if mode == "greyfield" and not codebase_content:
        console.print("[red]Error: Greyfield mode requires --codebase argument[/red]")
        sys.exit(1)

    # Run the factory
    console.print(f"\n[bold]Running Meta-Factory...[/bold]")
    console.print(f"  [dim]Client:[/dim] {client_name}")
    console.print(f"  [dim]Max cost:[/dim] ${max_cost or settings.max_cost_per_run_usd}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=None)

        result = run_factory(
            input_content=input_content,
            client_name=client_name,
            input_path=input_path,
            codebase_content=codebase_content,
            force_mode=force_mode,
            max_cost_usd=max_cost,
            provider=provider,
            model=model,
            quality=quality,
            hourly_rate=hourly_rate,
        )

        progress.update(task, completed=True)

    # Display results
    console.print("\n" + "=" * 60)

    if result.get("status") == "error":
        console.print(f"[red]Error:[/red] {result.get('error')}")
        sys.exit(1)

    console.print(f"[green]Status:[/green] {result.get('status', 'unknown')}")
    console.print(f"[green]Run ID:[/green] {result.get('run_id')}")
    console.print(f"[green]Mode:[/green] {result.get('mode')}")
    console.print(f"[green]Duration:[/green] {result.get('duration_seconds', 0):.1f}s")

    # Token usage
    token_usage = result.get("token_usage", {})
    if token_usage:
        console.print("\n[bold]Cost Summary:[/bold]")
        console.print(f"  Input tokens:  {token_usage.get('input_tokens', 0):,}")
        console.print(f"  Output tokens: {token_usage.get('output_tokens', 0):,}")
        console.print(f"  Total cost:    ${token_usage.get('cost_usd', 0):.4f}")

    # Artifacts
    artifacts = result.get("artifacts", {})
    if artifacts:
        console.print(f"\n[bold]Artifacts produced:[/bold]")
        for name in artifacts.keys():
            console.print(f"  - {name}")

    # Escalations
    escalations = result.get("escalations", [])
    if escalations:
        console.print(f"\n[yellow]Escalations ({len(escalations)}):[/yellow]")
        for esc in escalations:
            console.print(f"  - {esc.reason}")

    # Output path
    output_path = result.get("output_path")
    if output_path:
        console.print(f"\n[bold]Output saved to:[/bold] {output_path}")

    console.print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
