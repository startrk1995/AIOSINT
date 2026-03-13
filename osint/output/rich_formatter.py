"""Rich-formatted OSINT output — color-coded panels with timing and summary table."""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from osint.core.result import OsintResult

_AI_COLORS = {"gemini": "blue", "claude": "magenta", "codex": "cyan"}


def format_result(
    result: OsintResult,
    console: Console | None = None,
    elapsed: float | None = None,
) -> None:
    """Print a Rich Panel for a single OsintResult."""
    if console is None:
        console = Console()

    elapsed_str = f"  ({elapsed:.1f}s)" if elapsed is not None else ""
    title = f"[bold]{result.agent}[/bold] → {result.target}{elapsed_str}"
    border_color = "green" if result.success else "red"

    content_parts = []
    ai_color = _AI_COLORS.get(result.ai_used, "white")
    status_text = "[green]✓ Success[/green]" if result.success else "[red]✗ Failed[/red]"
    content_parts.append(f"AI: [{ai_color}]{result.ai_used}[/{ai_color}]   Status: {status_text}")

    if result.error:
        content_parts.append(f"[red]Error: {result.error}[/red]")

    if result.data:
        content_parts.append("\n[bold]Data:[/bold]")
        for key, value in result.data.items():
            content_parts.append(_render_field(key, value))

    if result.pivots:
        by_type: dict[str, list[str]] = {}
        for pivot in result.pivots:
            by_type.setdefault(pivot.type, []).append(pivot.value)
        content_parts.append(f"\n[bold]Pivots ({len(result.pivots)}):[/bold]")
        for ptype, values in by_type.items():
            color = _AI_COLORS.get(ptype, "yellow")
            for v in values:
                content_parts.append(f"  [{color}]{ptype}[/{color}]: {v}")

    content_parts.append(f"\n[dim]Timestamp: {result.timestamp}[/dim]")

    console.print(Panel(
        "\n".join(content_parts),
        title=title,
        border_style=border_color,
        expand=False,
    ))


def _render_field(key: str, value) -> str:
    if isinstance(value, list):
        if not value:
            return f"  {key}: (none)"
        lines = [f"  [bold]{key}:[/bold]"]
        for item in value:
            lines.append(f"    • {item}")
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = [f"  [bold]{key}:[/bold]"]
        for k, v in value.items():
            lines.append(f"    {k}: {v}")
        return "\n".join(lines)
    return f"  {key}: {value}"


def format_results(
    results: list[OsintResult],
    console: Console | None = None,
    context=None,
) -> None:
    """Print Rich Panels for each result, then a summary Table.

    Args:
        results: List of OsintResults to display.
        console: Rich Console to use (defaults to new Console()).
        context: Optional RunContext — reads context._timings for elapsed time column.
                 No other fields are accessed. If context is None, Time column is omitted.
    """
    if console is None:
        console = Console()

    timings: dict[str, float] = context._timings if context is not None else {}

    for result in results:
        elapsed = timings.get(f"{result.agent}:{result.target}")
        format_result(result, console=console, elapsed=elapsed)

    # Summary table
    table = Table(title="Summary", show_header=True, header_style="bold")
    table.add_column("Agent")
    table.add_column("Target")
    table.add_column("Status")
    show_time = bool(timings)
    if show_time:
        table.add_column("Time")
    table.add_column("Pivots")

    for result in results:
        status = "[green]✓[/green]" if result.success else "[red]✗[/red]"
        row = [result.agent, result.target, status]
        if show_time:
            t = timings.get(f"{result.agent}:{result.target}")
            row.append(f"{t:.1f}s" if t is not None else "—")
        row.append(str(len(result.pivots)))
        table.add_row(*row)

    console.print(table)
