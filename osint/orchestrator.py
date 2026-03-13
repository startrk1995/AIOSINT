"""OSINT orchestrator — BFS pivot chaining engine."""
import asyncio
from collections import deque
from datetime import datetime, timezone
from osint.core import OsintResult
from osint.agents import AGENT_REGISTRY


class OSINTOrchestrator:
    """Runs OSINT research with BFS pivot chaining.

    Starting from a seed (agent_type, target), runs the agent and collects
    pivots from the result. Each pivot becomes a new (agent_type, target) pair
    enqueued for the next BFS level. Visited pairs are tracked to prevent cycles.
    """

    async def run(
        self,
        target: str,
        agent_type: str,
        max_depth: int = 2,
    ) -> list[OsintResult]:
        """Run BFS pivot chaining starting from seed.

        Args:
            target: The initial research target (email, domain, etc.)
            agent_type: The type of agent to start with ("email", "domain", etc.)
            max_depth: Maximum BFS depth (default 2)

        Returns:
            List of all OsintResult objects collected during BFS
        """
        results: list[OsintResult] = []
        visited: set[tuple[str, str]] = set()

        # Queue entries: (agent_type, target, depth)
        queue: deque[tuple[str, str, int]] = deque()
        queue.append((agent_type, target, 0))

        while queue:
            # Collect all items at current depth level
            level_items = []
            current_depth = queue[0][2]
            while queue and queue[0][2] == current_depth:
                level_items.append(queue.popleft())

            # Filter already-visited
            level_items = [
                (at, t, d) for at, t, d in level_items
                if (at, t) not in visited
            ]

            if not level_items:
                continue

            # Mark visited
            for at, t, _ in level_items:
                visited.add((at, t))

            # Run all items at this level concurrently
            tasks = []
            for at, t, _ in level_items:
                if at in AGENT_REGISTRY:
                    run_fn, _ = AGENT_REGISTRY[at]
                    tasks.append(run_fn(t))

            level_results = await asyncio.gather(*tasks, return_exceptions=True)

            for item, result in zip(level_items, level_results):
                at, t, depth = item
                if isinstance(result, Exception):
                    # Create a failed OsintResult for exceptions from gather
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

                results.append(result)

                # Enqueue pivots for next level if within depth limit
                if depth < max_depth - 1:
                    for pivot in result.pivots:
                        if (pivot.type, pivot.value) not in visited:
                            queue.append((pivot.type, pivot.value, depth + 1))

        return results
