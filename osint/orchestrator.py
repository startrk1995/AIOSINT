"""OSINT orchestrator — BFS pivot chaining engine."""
import asyncio
from collections import deque
from datetime import datetime, timezone

from rich.console import Console
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from osint.core import OsintResult
from osint.core.run_context import RunContext
from osint.agents import AGENT_REGISTRY


class OSINTOrchestrator:
    """Runs OSINT research with BFS pivot chaining."""

    async def run(
        self,
        target: str,
        agent_type: str,
        max_depth: int = 2,
        context: RunContext | None = None,
    ) -> list[OsintResult]:
        """Run BFS pivot chaining starting from seed.

        All Live display activity happens inside this method. Result panel
        printing is the caller's responsibility — it must happen AFTER this
        method returns (i.e., after Live has exited).
        """
        results: list[OsintResult] = []
        visited: set[tuple[str, str]] = set()
        queue: deque[tuple[str, str, int]] = deque()
        queue.append((agent_type, target, 0))

        # Build Rich progress unconditionally; assign to context if one was provided
        shared_console = Console()
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.fields[agent_label]}[/bold]"),
            TextColumn("{task.fields[target_label]}"),
            TextColumn("[dim]{task.fields[ai_label]}[/dim]"),
            TimeElapsedColumn(),
            TextColumn("{task.fields[status_label]}"),
            console=shared_console,
        )

        if context is not None and context.progress is None:
            context.progress = progress

        with Live(progress, console=shared_console, refresh_per_second=4):
            while queue:
                level_items = []
                current_depth = queue[0][2]
                while queue and queue[0][2] == current_depth:
                    level_items.append(queue.popleft())

                level_items = [
                    (at, t, d) for at, t, d in level_items
                    if (at, t) not in visited
                ]
                if not level_items:
                    continue

                for at, t, _ in level_items:
                    visited.add((at, t))

                tasks = []
                task_items = []
                progress_task_ids = {}

                for at, t, depth in level_items:
                    if at in AGENT_REGISTRY:
                        run_fn, ai_cli = AGENT_REGISTRY[at]
                        # Add a progress row for this agent
                        tid = progress.add_task(
                            "",
                            agent_label=f"[{at}]",
                            target_label=t[:50],
                            ai_label=ai_cli,
                            status_label="",
                        )
                        progress_task_ids[(at, t)] = tid
                        tasks.append(run_fn(t, context=context))
                        task_items.append((at, t, depth))

                level_results = await asyncio.gather(*tasks, return_exceptions=True)

                for (at, t, depth), result in zip(task_items, level_results):
                    tid = progress_task_ids.get((at, t))

                    if isinstance(result, Exception):
                        if tid is not None:
                            is_timeout = "TIMEOUT" in str(result)
                            progress.update(
                                tid,
                                status_label="[yellow]TIMEOUT[/yellow]" if is_timeout else "[red]FAILED[/red]",
                                completed=100,  # 100 out of default total=100 → finished; True would be 1/100
                            )
                            progress.stop_task(tid)
                        results.append(OsintResult(
                            agent=at,
                            target=t,
                            ai_used=AGENT_REGISTRY[at][1] if at in AGENT_REGISTRY else "unknown",
                            success=False,
                            data={},
                            pivots=[],
                            raw_response="",
                            error=f"{type(result).__name__}: {result}",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        ))
                        continue

                    if tid is not None:
                        progress.update(
                            tid,
                            status_label="[green]done[/green]" if result.success else "[red]failed[/red]",
                            completed=100,  # 100/100 = finished; stops the spinner
                        )
                        progress.stop_task(tid)

                    results.append(result)

                    if depth < max_depth - 1:
                        for pivot in result.pivots:
                            if (pivot.type, pivot.value) not in visited:
                                queue.append((pivot.type, pivot.value, depth + 1))

        # Live has exited here — caller (CLI) prints panels
        return results
