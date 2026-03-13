"""OSINT agent for domain research using Gemini."""
import asyncio
from datetime import datetime, timezone
from osint.core import OsintResult, PivotEntity, AIRunner, AgentError, PromptBuilder, parse_json_response

AGENT_TYPE = "domain"
AI_CLI = "gemini"


async def run(target: str) -> OsintResult:
    """Run domain research on target."""
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        prompt = PromptBuilder().build(AGENT_TYPE, AI_CLI, target)
        raw = await AIRunner().run(AI_CLI, prompt)
        parsed = parse_json_response(raw)
        return OsintResult(
            agent=AGENT_TYPE,
            target=target,
            ai_used=AI_CLI,
            success=bool(parsed.get("found", False)),
            data=parsed.get("data", {}),
            pivots=[PivotEntity(**p) for p in parsed.get("pivots", [])],
            raw_response=raw,
            error=None,
            timestamp=timestamp,
        )
    except Exception as e:
        return OsintResult(
            agent=AGENT_TYPE,
            target=target,
            ai_used=AI_CLI,
            success=False,
            data={},
            pivots=[],
            raw_response="",
            error=str(e),
            timestamp=timestamp,
        )
