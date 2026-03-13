from rich.console import Console
from rich.panel import Panel
from rich.tree import Tree
from rich.text import Text
from osint.core.result import OsintResult

console = Console()


def format_result(result: OsintResult) -> None:
    """
    Print a Rich Panel for a single OsintResult.

    Args:
        result: OsintResult to format and display
    """
    # Build panel title
    title = f"[bold]{result.agent}[/bold] → {result.target}"

    # Determine border color based on success
    border_color = "green" if result.success else "red"

    # Build panel content
    content_parts = []

    # AI used and status
    status_text = "[green]✓ Success[/green]" if result.success else "[red]✗ Failed[/red]"
    content_parts.append(f"AI: {result.ai_used}")
    content_parts.append(f"Status: {status_text}")

    # Error message if present
    if result.error:
        content_parts.append(f"[red]Error: {result.error}[/red]")

    # Data fields
    if result.data:
        content_parts.append("\n[bold]Data:[/bold]")
        for key, value in result.data.items():
            content_parts.append(f"  {key}: {value}")

    # Pivots
    if result.pivots:
        content_parts.append(f"\n[bold]Pivots ({len(result.pivots)}):[/bold]")
        for pivot in result.pivots:
            content_parts.append(f"  • {pivot.type}: {pivot.value}")

    # Timestamp
    content_parts.append(f"\n[dim]Timestamp: {result.timestamp}[/dim]")

    # Join content and create panel
    content = "\n".join(content_parts)

    panel = Panel(
        content,
        title=title,
        border_style=border_color,
        expand=False
    )

    console.print(panel)


def format_results(results: list[OsintResult]) -> None:
    """
    Print Rich Panels for each result and summary statistics.

    Args:
        results: List of OsintResults to format and display
    """
    for result in results:
        format_result(result)

    # Summary line
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful
    total_pivots = sum(len(r.pivots) for r in results)

    summary = (
        f"[bold]Summary:[/bold] {total} results, {successful} successful, "
        f"{failed} failed, {total_pivots} pivots discovered"
    )

    console.print(summary)
