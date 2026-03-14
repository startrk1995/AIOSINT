"""OSINT CLI — entry point for the osint command."""
import asyncio
import shutil
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from osint.agents import AGENT_REGISTRY
from osint.config import settings
from osint.core.run_context import RunContext
from osint.orchestrator import OSINTOrchestrator
from osint.output import rich_formatter, json_formatter, report_formatter

app = typer.Typer(
    name="osint",
    help="OSINT meta-framework: delegates research to Gemini, Claude, or Codex CLI tools.",
    add_completion=False,
)
console = Console()


def _check_binaries() -> None:
    required = {
        "gemini": settings.gemini_path,
        "claude": settings.claude_path,
        "codex": settings.codex_path,
    }
    for name, path in required.items():
        if not shutil.which(path):
            console.print(f"[yellow]Warning: {name} CLI not found at '{path}'[/yellow]")


def _make_progress(shared_console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.fields[agent_label]}[/bold]"),
        TextColumn("{task.fields[target_label]}"),
        TextColumn("[dim]{task.fields[ai_label]}[/dim]"),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status_label]}"),
        console=shared_console,
    )


def _run_agent(agent_type: str, target: str, verbose: bool = False) -> None:
    """Run a single agent with live status display."""
    _check_binaries()
    run_fn, ai_cli = AGENT_REGISTRY[agent_type]

    shared_console = Console()
    progress = _make_progress(shared_console)
    context = RunContext(verbose=verbose, progress=progress)

    tid = progress.add_task(
        "",
        agent_label=f"[{agent_type}]",
        target_label=target[:50],
        ai_label=ai_cli,
        status_label="",
    )

    try:
        with Live(progress, console=shared_console, refresh_per_second=4):
            result = asyncio.run(run_fn(target, context=context))
            is_timeout = result.error and "TIMEOUT" in result.error
            progress.update(
                tid,
                status_label="[yellow]TIMEOUT[/yellow]" if is_timeout
                             else "[green]done[/green]" if result.success
                             else "[red]failed[/red]",
                completed=100,  # 100/100 = finished; stops spinner
            )
            progress.stop_task(tid)
        # Live has exited — safe to print
        # Timing key uses agent_type and target, same format as base.py writes
        rich_formatter.format_result(result, console=shared_console, elapsed=context._timings.get(f"{agent_type}:{target}"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]", err=True)
        raise typer.Exit(code=1)


@app.command()
def email(
    target: str = typer.Argument(..., help="Email address to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate an email address using Gemini."""
    _run_agent("email", target, verbose=verbose)


@app.command()
def phone(
    target: str = typer.Argument(..., help="Phone number to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate a phone number using Claude."""
    _run_agent("phone", target, verbose=verbose)


@app.command()
def domain(
    target: str = typer.Argument(..., help="Domain name to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate a domain name using Gemini."""
    _run_agent("domain", target, verbose=verbose)


@app.command()
def username(
    target: str = typer.Argument(..., help="Username to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate a username using Codex."""
    _run_agent("username", target, verbose=verbose)


@app.command()
def name(
    target: str = typer.Argument(..., help="Person's full name to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate a person by name using Claude."""
    _run_agent("person", target, verbose=verbose)


@app.command()
def location(
    target: str = typer.Argument(..., help="Location or address to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate a location or address using Codex."""
    _run_agent("location", target, verbose=verbose)


@app.command()
def image(
    target: str = typer.Argument(..., help="Path to image file to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate an image file using Codex."""
    _run_agent("image", target, verbose=verbose)


@app.command()
def social(
    target: str = typer.Argument(..., help="Social media handle to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate a social media handle using Codex."""
    _run_agent("social", target, verbose=verbose)


@app.command()
def ip(
    target: str = typer.Argument(..., help="IP address to investigate"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
):
    """Investigate an IP address using Gemini."""
    _run_agent("ip", target, verbose=verbose)


@app.command()
def recon(
    target: str = typer.Argument(..., help="Starting target (email, domain, etc.)"),
    agent: str = typer.Option("email", help=f"Starting agent type. Choices: {', '.join(sorted(AGENT_REGISTRY.keys()))}"),
    depth: int = typer.Option(2, min=1, max=10, help="BFS pivot depth (1-10)"),
    output: str = typer.Option("rich", help="Output format: rich, json, or report"),
    save: Optional[str] = typer.Option(None, help="Save output to this filepath"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show prompts and raw AI responses"),
    timeout: float = typer.Option(90.0, help="Per-agent timeout in seconds"),
    timeout_action: str = typer.Option("warn", help="On timeout: warn (yellow row) or kill (red row)"),
):
    """Run full auto-pivot OSINT recon starting from a target."""
    _check_binaries()

    if agent not in AGENT_REGISTRY:
        console.print(
            f"[red]Error: Unknown agent '{agent}'. Valid: {', '.join(sorted(AGENT_REGISTRY.keys()))}[/red]",
            err=True,
        )
        raise typer.Exit(code=1)

    if output not in ("rich", "json", "report"):
        console.print(
            f"[red]Error: Invalid output format '{output}'. Choose 'rich', 'json', or 'report'[/red]",
            err=True,
        )
        raise typer.Exit(code=1)

    if timeout_action not in ("warn", "kill"):
        console.print(
            f"[red]Error: Invalid timeout-action '{timeout_action}'. Choose 'warn' or 'kill'[/red]",
            err=True,
        )
        raise typer.Exit(code=1)

    context = RunContext(verbose=verbose, timeout=timeout, timeout_action=timeout_action)

    try:
        orchestrator = OSINTOrchestrator()
        results = asyncio.run(
            orchestrator.run(target, agent, max_depth=depth, context=context)
        )
    except Exception as e:
        console.print(f"[red]Recon failed: {e}[/red]", err=True)
        raise typer.Exit(code=1)

    # Live has exited inside orchestrator.run() — safe to print now
    if output == "rich":
        rich_formatter.format_results(results, context=context)
    elif output == "json":
        console.print(json_formatter.format_results(results))
    elif output == "report":
        report_formatter.format_results(results, context=context)

    if save:
        if output == "report":
            report_formatter.save_results(results, save, context=context)
        else:
            json_formatter.save_results(results, save)
        console.print(f"[green]Results saved to {save}[/green]")
