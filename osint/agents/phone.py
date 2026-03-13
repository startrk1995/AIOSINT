"""OSINT phone research agent using Claude CLI."""
import re
from osint.agents.base import make_run_fn
from osint.core.result import OsintResult
from osint.core.run_context import RunContext

AGENT_TYPE = "phone"
AI_CLI = "claude"

_base_run = make_run_fn(AGENT_TYPE, AI_CLI)


def normalize_phone(number: str) -> str:
    """Normalize US phone numbers to NXX-NXX-XXXX format.

    Handles: +1-555-999-0202, 1-555-999-0202, (555) 999-0202,
             555.999.0202, 5559990202, 555-999-0202.
    Non-US numbers (>10 significant digits) are returned unchanged.
    """
    # Strip leading +1 or 1 country code
    stripped = re.sub(r"^\+?1[-.\s]?", "", number.strip())
    # Remove all non-digit characters to count significant digits
    digits_only = re.sub(r"\D", "", stripped)
    if len(digits_only) != 10:
        # Not a standard US number — pass through unchanged
        return number
    # Format as NXX-NXX-XXXX
    return f"{digits_only[:3]}-{digits_only[3:6]}-{digits_only[6:]}"


async def run(target: str, context: RunContext | None = None) -> OsintResult:
    """Run phone OSINT with normalization applied before research."""
    target = normalize_phone(target)
    return await _base_run(target, context=context)
