"""Base agent factory for OSINT agents."""
import time
from datetime import datetime, timezone
from osint.core import OsintResult, PivotEntity, AIRunner, PromptBuilder, parse_json_response
from osint.core.run_context import RunContext


def make_run_fn(agent_type: str, ai_cli: str):
    """Return an async run(target, context=None) function for the given agent_type and ai_cli."""

    async def run(target: str, context: RunContext | None = None) -> OsintResult:
        """Run OSINT research on target."""
        timestamp = datetime.now(timezone.utc).isoformat()
        raw = ""
        start = time.monotonic()
        try:
            prompt = PromptBuilder().build(agent_type, ai_cli, target)
            raw = await AIRunner().run(ai_cli, prompt, context=context)
            parsed = parse_json_response(raw)
            pivots = []
            for p in parsed.get("pivots", []):
                try:
                    pivots.append(PivotEntity(**p))
                except Exception:
                    pass  # skip malformed pivots
            result = OsintResult(
                agent=agent_type,
                target=target,
                ai_used=ai_cli,
                success=bool(parsed.get("found", False)),
                data=parsed.get("data", {}),
                pivots=pivots,
                raw_response=raw,
                error=None,
                timestamp=timestamp,
            )
        except Exception as e:
            result = OsintResult(
                agent=agent_type,
                target=target,
                ai_used=ai_cli,
                success=False,
                data={},
                pivots=[],
                raw_response=raw,
                error=f"{type(e).__name__}: {e}",
                timestamp=timestamp,
            )
        finally:
            if context is not None:
                elapsed = time.monotonic() - start
                context._timings[f"{agent_type}:{target}"] = elapsed

        return result

    return run
