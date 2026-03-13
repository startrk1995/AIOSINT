"""OSINT CLI — entry point for the osint command."""
import asyncio
import shutil
from typing import Optional

import typer
from rich.console import Console

from osint.agents import AGENT_REGISTRY
from osint.config import settings
from osint.orchestrator import OSINTOrchestrator
from osint.output import rich_formatter, json_formatter

app = typer.Typer(
    name="osint",
    help="OSINT meta-framework: delegates research to Gemini, Claude, or Codex CLI tools.",
    add_completion=False,
)
console = Console()


def _check_binaries() -> None:
    """Warn if required AI CLI binaries are missing."""
    required = {
        "gemini": settings.gemini_path,
        "claude": settings.claude_path,
        "codex": settings.codex_path,
    }
    for name, path in required.items():
        if not shutil.which(path):
            console.print(f"[yellow]Warning: {name} CLI not found at '{path}'[/yellow]")


def _run_agent(agent_type: str, target: str) -> None:
    """Run a single agent and display results with Rich."""
    _check_binaries()
    try:
        run_fn, _ = AGENT_REGISTRY[agent_type]
        result = asyncio.run(run_fn(target))
        rich_formatter.format_result(result)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", err=True)
        raise typer.Exit(code=1)


@app.command()
def email(target: str = typer.Argument(..., help="Email address to investigate")):
    """Investigate an email address using Gemini."""
    _run_agent("email", target)


@app.command()
def phone(target: str = typer.Argument(..., help="Phone number to investigate")):
    """Investigate a phone number using Claude."""
    _run_agent("phone", target)


@app.command()
def domain(target: str = typer.Argument(..., help="Domain name to investigate")):
    """Investigate a domain name using Gemini."""
    _run_agent("domain", target)


@app.command()
def username(target: str = typer.Argument(..., help="Username to investigate")):
    """Investigate a username using Codex."""
    _run_agent("username", target)


@app.command()
def name(target: str = typer.Argument(..., help="Person's full name to investigate")):
    """Investigate a person by name using Claude."""
    _run_agent("person", target)


@app.command()
def location(target: str = typer.Argument(..., help="Location or address to investigate")):
    """Investigate a location or address using Codex."""
    _run_agent("location", target)


@app.command()
def image(target: str = typer.Argument(..., help="Path to image file to investigate")):
    """Investigate an image file using Codex."""
    _run_agent("image", target)


@app.command()
def social(target: str = typer.Argument(..., help="Social media handle to investigate")):
    """Investigate a social media handle using Codex."""
    _run_agent("social", target)


@app.command()
def recon(
    target: str = typer.Argument(..., help="Starting target (email, domain, etc.)"),
    agent: str = typer.Option("email", help=f"Starting agent type. Choices: {', '.join(sorted(AGENT_REGISTRY.keys()))}"),
    depth: int = typer.Option(2, min=1, max=10, help="BFS pivot depth (1-10)"),
    output: str = typer.Option("rich", help="Output format: rich or json"),
    save: Optional[str] = typer.Option(None, help="Save JSON output to this filepath"),
):
    """Run full auto-pivot OSINT recon starting from a target."""
    _check_binaries()

    # Validate inputs
    if agent not in AGENT_REGISTRY:
        console.print(
            f"[red]Error: Unknown agent '{agent}'. Valid: {', '.join(sorted(AGENT_REGISTRY.keys()))}[/red]",
            err=True,
        )
        raise typer.Exit(code=1)

    if output not in ("rich", "json"):
        console.print(
            f"[red]Error: Invalid output format '{output}'. Choose 'rich' or 'json'[/red]",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        orchestrator = OSINTOrchestrator()
        results = asyncio.run(orchestrator.run(target, agent, max_depth=depth))
    except Exception as e:
        console.print(f"[red]Recon failed: {e}[/red]", err=True)
        raise typer.Exit(code=1)

    should_json = output == "json"
    should_save = save is not None

    if output == "rich":
        rich_formatter.format_results(results)

    if should_json:
        console.print(json_formatter.format_results(results))

    if should_save:
        json_formatter.save_results(results, save)
        console.print(f"[green]Results saved to {save}[/green]")
