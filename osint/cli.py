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


@app.command()
def email(target: str = typer.Argument(..., help="Email address to investigate")):
    """Investigate an email address using Gemini."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["email"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def phone(target: str = typer.Argument(..., help="Phone number to investigate")):
    """Investigate a phone number using Claude."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["phone"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def domain(target: str = typer.Argument(..., help="Domain name to investigate")):
    """Investigate a domain name using Gemini."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["domain"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def username(target: str = typer.Argument(..., help="Username to investigate")):
    """Investigate a username using Codex."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["username"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def name(target: str = typer.Argument(..., help="Person's full name to investigate")):
    """Investigate a person by name using Claude."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["person"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def location(target: str = typer.Argument(..., help="Location or address to investigate")):
    """Investigate a location or address using Codex."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["location"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def image(target: str = typer.Argument(..., help="Path to image file to investigate")):
    """Investigate an image file using Codex."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["image"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def social(target: str = typer.Argument(..., help="Social media handle to investigate")):
    """Investigate a social media handle using Codex."""
    _check_binaries()
    run_fn, _ = AGENT_REGISTRY["social"]
    result = asyncio.run(run_fn(target))
    rich_formatter.format_result(result)


@app.command()
def recon(
    target: str = typer.Argument(..., help="Starting target (email, domain, etc.)"),
    agent: str = typer.Option("email", help="Starting agent type"),
    depth: int = typer.Option(2, help="BFS pivot depth"),
    output: str = typer.Option("rich", help="Output format: rich or json"),
    save: Optional[str] = typer.Option(None, help="Save JSON output to this filepath"),
):
    """Run full auto-pivot OSINT recon starting from a target."""
    _check_binaries()
    orchestrator = OSINTOrchestrator()
    results = asyncio.run(orchestrator.run(target, agent, max_depth=depth))

    if output == "json" or save:
        json_output = json_formatter.format_results(results)
        if output == "json":
            console.print(json_output)
        if save:
            json_formatter.save_results(results, save)
            console.print(f"[green]Results saved to {save}[/green]")
    else:
        rich_formatter.format_results(results)
