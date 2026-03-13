"""RunContext — shared execution context threaded through the OSINT call stack."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.progress import Progress


@dataclass
class RunContext:
    """Carries verbose flag, timeout config, and a shared Rich Progress handle.

    Constructed in CLI, threaded through orchestrator → make_run_fn → AIRunner.
    """
    verbose: bool = False
    timeout: float = 90.0
    timeout_action: str = "warn"   # "warn" | "kill" — both kill the subprocess; cosmetic only
    progress: "Progress | None" = None
    _timings: dict[str, float] = field(default_factory=dict)
