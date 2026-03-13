"""Plain-text narrative OSINT report — no Rich markup, safe to pipe or save."""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from typing import TextIO

from osint.core.result import OsintResult
from osint.core.run_context import RunContext

_SEP_WIDE = "═" * 44
_SEP_THIN = "─" * 44


def format_results(
    results: list[OsintResult],
    stream: TextIO | None = None,
    context: RunContext | None = None,
) -> None:
    """Print a plain-text narrative OSINT report.

    Args:
        results: List of OsintResults to include.
        stream: Output stream (defaults to sys.stdout).
        context: Optional RunContext — reads _timings and timeout. No other fields accessed.
    """
    if stream is None:
        stream = sys.stdout

    timings: dict[str, float] = context._timings if context is not None else {}
    timeout: float = context.timeout if context is not None else 90.0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    seed = results[0].target if results else "unknown"
    total_elapsed = sum(timings.values())
    mins, secs = divmod(int(total_elapsed), 60)
    duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"

    out = stream.write

    out(f"{_SEP_WIDE}\n")
    out(f"  OSINT REPORT  —  {seed}\n")
    out(f"  Generated: {now}\n")
    out(f"{_SEP_WIDE}\n\n")

    out("TARGET SUMMARY\n")
    out(f"  Seed: {seed}  |  Agents: {len(results)}  |  Duration: {duration_str}\n\n")

    for result in results:
        label = result.agent.upper()
        out(f"── {label} {'─' * max(0, 42 - len(label))}\n")
        elapsed = timings.get(f"{result.agent}:{result.target}")
        if elapsed is not None:
            out(f"  Target: {result.target}  ({elapsed:.1f}s)\n")
        else:
            out(f"  Target: {result.target}\n")

        if result.error:
            is_timeout = "TIMEOUT" in result.error
            if is_timeout:
                out(f"  [TIMEOUT] {result.agent}: {result.target} — exceeded {timeout:.0f}s\n\n")
            else:
                out(f"  [FAILED] {result.agent}: {result.target} — {result.error}\n\n")
            continue

        if result.data:
            for key, value in result.data.items():
                out(_format_field(key, value))

        if result.pivots:
            out("\n  Pivots\n")
            by_type: dict[str, list[str]] = {}
            for p in result.pivots:
                by_type.setdefault(p.type, []).append(p.value)
            for ptype, values in by_type.items():
                for v in values:
                    out(f"    → {ptype}: {v}\n")

        out("\n")


def _format_field(key: str, value) -> str:
    label = f"  {key}"
    dots = "." * max(1, 20 - len(label))
    if isinstance(value, list):
        if not value:
            return f"{label} {dots} (none)\n"
        MAX = 3
        shown = ", ".join(str(v) for v in value[:MAX])
        extra = f" (+{len(value) - MAX} more)" if len(value) > MAX else ""
        return f"{label} {dots} {shown}{extra}\n"
    if isinstance(value, dict):
        lines = [f"{label}:\n"]
        for k, v in value.items():
            lines.append(f"    {k}: {v}\n")
        return "".join(lines)
    return f"{label} {dots} {value}\n"


def save_results(
    results: list[OsintResult],
    filepath: str,
    context: RunContext | None = None,
) -> None:
    """Write plain-text report to a .txt file."""
    try:
        with open(filepath, "w") as f:
            format_results(results, stream=f, context=context)
    except OSError as e:
        raise OSError(f"Failed to save report to {filepath}: {e}") from e
