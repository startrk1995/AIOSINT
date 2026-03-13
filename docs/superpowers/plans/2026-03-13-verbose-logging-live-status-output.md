# Verbose Logging, Live Status, Timeouts & Enhanced Output — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--verbose` logging, live terminal status spinners, per-agent timeouts, and enhanced Rich + plain-text report output to the OSINT framework.

**Architecture:** A `RunContext` dataclass is constructed in the CLI and threaded through `orchestrator → make_run_fn → AIRunner`. Context carries the verbose flag, timeout setting, and a shared Rich `Progress` handle. Output is sequenced: Live runs during execution, all panel printing happens after `Live.__exit__()`.

**Spec:** `docs/superpowers/specs/2026-03-13-verbose-logging-live-status-output-design.md`

**Tech Stack:** Python 3.11+, asyncio, Rich (Live, Progress, Table, Panel, Console), Typer, pytest, pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `osint/core/run_context.py` | **Create** | RunContext dataclass — verbose, timeout, progress, timings |
| `osint/core/__init__.py` | Modify | Export RunContext |
| `osint/core/ai_runner.py` | Modify | Accept context; subprocess timeout+kill lifecycle; verbose logging |
| `osint/agents/base.py` | Modify | Thread context into run_fn; update progress row; record timings |
| `osint/agents/phone.py` | Modify | Expand 6-line wrapper to include normalize_phone() |
| `osint/agents/__init__.py` | Modify | Update AGENT_REGISTRY type annotation |
| `osint/orchestrator.py` | Modify | Thread context; open/close Live display; output sequencing |
| `osint/cli.py` | Modify | --verbose/-v flag; --timeout/--timeout-action on recon; --output report; Live in _run_agent |
| `osint/output/rich_formatter.py` | Modify | console+elapsed params; better data rendering; summary Table |
| `osint/output/report_formatter.py` | **Create** | Plain-text narrative report |
| `osint/output/__init__.py` | Modify | Export report_formatter |
| `pyproject.toml` | Modify | Add pytest + pytest-asyncio dev dependencies |
| `tests/__init__.py` | **Create** | Test package |
| `tests/core/__init__.py` | **Create** | |
| `tests/core/test_run_context.py` | **Create** | RunContext tests |
| `tests/core/test_ai_runner.py` | **Create** | AIRunner timeout + verbose tests |
| `tests/agents/__init__.py` | **Create** | |
| `tests/agents/test_base.py` | **Create** | Context threading + timings tests |
| `tests/agents/test_phone.py` | **Create** | Phone normalization tests |
| `tests/output/__init__.py` | **Create** | |
| `tests/output/test_rich_formatter.py` | **Create** | Enhanced formatter tests |
| `tests/output/test_report_formatter.py` | **Create** | Report formatter tests |

---

## Chunk 1: Foundation — RunContext, AIRunner, base.py, phone normalization

### Task 1: Test infrastructure + RunContext

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`, `tests/core/__init__.py`
- Create: `tests/core/test_run_context.py`
- Create: `osint/core/run_context.py`

- [ ] **Step 1: Add pytest to pyproject.toml**

Edit `pyproject.toml` to add:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Install: `pip install -e ".[dev]"`

- [ ] **Step 2: Create test package structure**

```bash
mkdir -p tests/core tests/agents tests/output
touch tests/__init__.py tests/core/__init__.py tests/agents/__init__.py tests/output/__init__.py
```

- [ ] **Step 3: Write failing tests for RunContext**

Create `tests/core/test_run_context.py`:
```python
from osint.core.run_context import RunContext


def test_defaults():
    ctx = RunContext()
    assert ctx.verbose is False
    assert ctx.timeout == 90.0
    assert ctx.timeout_action == "warn"
    assert ctx.progress is None
    assert ctx._timings == {}


def test_verbose_flag():
    ctx = RunContext(verbose=True)
    assert ctx.verbose is True


def test_custom_timeout():
    ctx = RunContext(timeout=30.0, timeout_action="kill")
    assert ctx.timeout == 30.0
    assert ctx.timeout_action == "kill"


def test_timings_mutable():
    ctx = RunContext()
    ctx._timings["email:foo@bar.com"] = 12.5
    assert ctx._timings["email:foo@bar.com"] == 12.5


def test_two_contexts_dont_share_timings():
    a = RunContext()
    b = RunContext()
    a._timings["x"] = 1.0
    assert "x" not in b._timings
```

- [ ] **Step 4: Run tests — expect ImportError (module doesn't exist yet)**

```bash
pytest tests/core/test_run_context.py -v
```
Expected: `ModuleNotFoundError: No module named 'osint.core.run_context'`

- [ ] **Step 5: Create `osint/core/run_context.py`**

```python
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
```

- [ ] **Step 6: Run tests — expect PASS**

```bash
pytest tests/core/test_run_context.py -v
```
Expected: 5 passed

- [ ] **Step 7: Export from `osint/core/__init__.py`**

Add to `osint/core/__init__.py`:
```python
from .run_context import RunContext
```
Add `"RunContext"` to `__all__`.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml tests/ osint/core/run_context.py osint/core/__init__.py
git commit -m "feat: add RunContext dataclass and test infrastructure"
```

---

### Task 2: AIRunner — timeout lifecycle

**Files:**
- Modify: `osint/core/ai_runner.py`
- Create: `tests/core/test_ai_runner.py`

- [ ] **Step 1: Write failing tests for timeout**

Create `tests/core/test_ai_runner.py`:
```python
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from osint.core.ai_runner import AIRunner, AgentError
from osint.core.run_context import RunContext


@pytest.fixture
def mock_process_fast():
    """Subprocess that returns immediately."""
    proc = MagicMock()
    proc.returncode = 0
    proc.kill = MagicMock()
    proc.communicate = AsyncMock(return_value=(b'{"found": true}', b""))
    return proc


@pytest.fixture
def mock_process_slow():
    """Subprocess that hangs forever."""
    async def slow_communicate():
        await asyncio.sleep(999)
        return b"", b""

    proc = MagicMock()
    proc.returncode = 0
    proc.kill = MagicMock()
    # Second call (reap after kill) returns immediately
    proc.communicate = AsyncMock(side_effect=[slow_communicate(), AsyncMock(return_value=(b"", b""))() ])
    return proc


async def test_run_no_context_succeeds(mock_process_fast):
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_fast):
        runner = AIRunner()
        result = await runner.run("gemini", "test prompt")
    assert '{"found": true}' in result


async def test_timeout_kill_raises_agent_error(mock_process_slow):
    ctx = RunContext(timeout=0.01, timeout_action="kill")
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_slow):
        runner = AIRunner()
        with pytest.raises(AgentError, match="TIMEOUT"):
            await runner.run("gemini", "test prompt", context=ctx)
    mock_process_slow.kill.assert_called_once()
    # Reap step must be called — "must not be omitted" per spec
    assert mock_process_slow.communicate.call_count == 2


async def test_timeout_warn_also_kills_process(mock_process_slow):
    """warn mode must still kill the OS process — distinction is cosmetic."""
    ctx = RunContext(timeout=0.01, timeout_action="warn")
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_slow):
        runner = AIRunner()
        with pytest.raises(AgentError, match="TIMEOUT"):
            await runner.run("gemini", "test prompt", context=ctx)
    mock_process_slow.kill.assert_called_once()
    # Reap step must be called — "must not be omitted" per spec
    assert mock_process_slow.communicate.call_count == 2


async def test_unsupported_ai_raises():
    runner = AIRunner()
    with pytest.raises(AgentError, match="Unsupported AI"):
        await runner.run("gpt4", "prompt")


async def test_subprocess_nonzero_raises(mock_process_fast):
    mock_process_fast.returncode = 1
    mock_process_fast.communicate = AsyncMock(return_value=(b"", b"error msg"))
    with patch("asyncio.create_subprocess_exec", return_value=mock_process_fast):
        runner = AIRunner()
        with pytest.raises(AgentError, match="subprocess failed"):
            await runner.run("gemini", "prompt")
```

- [ ] **Step 2: Run tests — expect failures (no context param yet)**

```bash
pytest tests/core/test_ai_runner.py -v
```
Expected: `TypeError: AIRunner.run() got an unexpected keyword argument 'context'`

- [ ] **Step 3: Update `osint/core/ai_runner.py`**

```python
import asyncio
from osint.config import settings
from osint.core.run_context import RunContext


class AgentError(Exception):
    pass


class AIRunner:
    """Dispatches prompts to AI CLI subprocesses (gemini, claude, codex)."""

    def _get_commands(self) -> dict[str, list[str]]:
        return {
            "gemini": [settings.gemini_path, "-p"],
            "claude": [settings.claude_path, "-p"],
            "codex": [settings.codex_path, "exec", "--full-auto", "--skip-git-repo-check"],
        }

    async def run(self, ai: str, prompt: str, context: RunContext | None = None) -> str:
        """Run the given AI CLI with the prompt and return stdout as a string."""
        commands = self._get_commands()
        if ai not in commands:
            raise AgentError(f"Unsupported AI: {ai!r}. Must be one of {list(commands)}")

        # Verbose: log the prompt being sent
        if context and context.verbose:
            _verbose_print(context, f"[dim cyan]→ [{ai}] prompt:[/dim cyan]\n{prompt}")

        cmd = commands[ai] + [prompt]
        timeout = context.timeout if context else None

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            if timeout is not None:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            else:
                stdout, stderr = await process.communicate()
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()  # reap zombie — must not be omitted
            raise AgentError(f"TIMEOUT after {timeout}s")

        if process.returncode != 0:
            raise AgentError(f"{ai} subprocess failed: {stderr.decode()}")

        result = stdout.decode()

        # Verbose: log the raw response
        if context and context.verbose:
            _verbose_print(context, f"[dim white]← [{ai}] response:[/dim white]\n{result}")

        return result


def _verbose_print(context: RunContext, message: str) -> None:
    """Print verbose output through the shared console, falling back to a new Console."""
    from rich.console import Console
    if context.progress is not None:
        context.progress.console.print(message)
    else:
        Console().print(message)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/core/test_ai_runner.py -v
```
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add osint/core/ai_runner.py tests/core/test_ai_runner.py
git commit -m "feat: add context param to AIRunner with timeout lifecycle and verbose logging"
```

---

### Task 3: agents/base.py — context threading + progress + timings

**Files:**
- Modify: `osint/agents/base.py`
- Create: `tests/agents/test_base.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_base.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from osint.agents.base import make_run_fn
from osint.core.run_context import RunContext


@pytest.fixture
def mock_ai_response():
    return '{"found": true, "data": {"name": "Test"}, "pivots": []}'


async def test_run_without_context(mock_ai_response):
    run = make_run_fn("email", "gemini")
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(return_value=mock_ai_response)):
        result = await run("test@example.com")
    assert result.success is True
    assert result.agent == "email"
    assert result.target == "test@example.com"


async def test_run_with_context_records_timing(mock_ai_response):
    run = make_run_fn("email", "gemini")
    ctx = RunContext()
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(return_value=mock_ai_response)):
        result = await run("test@example.com", context=ctx)
    assert "email:test@example.com" in ctx._timings
    assert ctx._timings["email:test@example.com"] > 0.0


async def test_run_error_records_timing_too():
    run = make_run_fn("email", "gemini")
    ctx = RunContext()
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(side_effect=Exception("boom"))):
        result = await run("test@example.com", context=ctx)
    assert result.success is False
    assert "email:test@example.com" in ctx._timings


async def test_run_passes_context_to_ai_runner(mock_ai_response):
    run = make_run_fn("email", "gemini")
    ctx = RunContext(timeout=30.0)
    with patch("osint.core.ai_runner.AIRunner.run", AsyncMock(return_value=mock_ai_response)) as mock_run:
        await run("test@example.com", context=ctx)
    assert mock_run.call_args.kwargs.get("context") is ctx
```

- [ ] **Step 2: Run tests — expect failures**

```bash
pytest tests/agents/test_base.py -v
```
Expected: failures because `run()` doesn't accept `context` yet

- [ ] **Step 3: Update `osint/agents/base.py`**

```python
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
                    pass
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/agents/test_base.py -v
```
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add osint/agents/base.py tests/agents/test_base.py
git commit -m "feat: thread RunContext through make_run_fn; record timings"
```

---

### Task 4: Phone normalization

**Files:**
- Modify: `osint/agents/phone.py`
- Create: `tests/agents/test_phone.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_phone.py`:
```python
import pytest
from osint.agents.phone import normalize_phone


@pytest.mark.parametrize("raw, expected", [
    ("+1-555-999-0202", "555-999-0202"),
    ("1-555-999-0202",  "555-999-0202"),
    ("5559990202",      "555-999-0202"),
    ("555-999-0202",    "555-999-0202"),
    ("(555) 999-0202",  "555-999-0202"),
    ("(555)999-0202",   "555-999-0202"),
    ("555.999.0202",    "555-999-0202"),
    # Non-US: pass through unchanged (>10 significant digits)
    ("+44-20-7946-0958", "+44-20-7946-0958"),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/agents/test_phone.py -v
```
Expected: `ImportError: cannot import name 'normalize_phone'`

- [ ] **Step 3: Expand `osint/agents/phone.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/agents/test_phone.py -v
```
Expected: 8 passed

- [ ] **Step 5: Update AGENT_REGISTRY type annotation in `osint/agents/__init__.py`**

Change line 7 from:
```python
AGENT_REGISTRY: dict[str, tuple[Callable[[str], Awaitable[OsintResult]], str]] = {
```
to:
```python
AGENT_REGISTRY: dict[str, tuple[Callable[..., Awaitable[OsintResult]], str]] = {
```

- [ ] **Step 6: Run full test suite to confirm nothing broken**

```bash
pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add osint/agents/phone.py osint/agents/__init__.py tests/agents/test_phone.py
git commit -m "feat: add phone number normalization; update AGENT_REGISTRY type annotation"
```

---

## Chunk 2: Integration — Orchestrator, Output, CLI

### Task 5: Orchestrator — Live display + context threading

**Files:**
- Modify: `osint/orchestrator.py`

*Note: The orchestrator's Live display is integration-level behavior (requires real Rich terminal + async subprocess). Unit-test the context-passing logic only; Live rendering is validated by manual smoke test at the end.*

**Spec deviation note:** The spec pseudocode shows the orchestrator printing panels after `Live.__exit__()`. This plan intentionally departs from that: the orchestrator is format-agnostic and returns `results` without printing anything. The CLI (Task 8) owns all output dispatch for all three modes (`rich`, `json`, `report`). This is architecturally cleaner and lets the spec's `pass` branch in the `rich` dispatch become `rich_formatter.format_results(results, context=context)`. Do NOT add any `rich_formatter` calls to the orchestrator.

- [ ] **Step 1: Rewrite `osint/orchestrator.py`**

```python
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

        if context is not None:
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

        # Live has exited here — caller prints panels
        return results
```

- [ ] **Step 2: Run existing tests to confirm no regressions**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add osint/orchestrator.py
git commit -m "feat: add Live progress display and RunContext threading to orchestrator"
```

---

### Task 6: Enhanced rich_formatter

**Files:**
- Modify: `osint/output/rich_formatter.py`
- Create: `tests/output/test_rich_formatter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/output/test_rich_formatter.py`:
```python
from io import StringIO
from rich.console import Console
from osint.output.rich_formatter import format_result, format_results
from osint.core.result import OsintResult, PivotEntity


def make_result(**kwargs):
    defaults = dict(
        agent="email", target="foo@bar.com", ai_used="gemini",
        success=True, data={}, pivots=[], raw_response="", error=None,
        timestamp="2026-03-13T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return OsintResult(**defaults)


def capture(fn, *args, **kwargs) -> str:
    buf = StringIO()
    console = Console(file=buf, no_color=True)
    fn(*args, console=console, **kwargs)
    return buf.getvalue()


def test_format_result_shows_agent_and_target():
    r = make_result()
    out = capture(format_result, r)
    assert "email" in out
    assert "foo@bar.com" in out


def test_format_result_shows_elapsed():
    r = make_result()
    out = capture(format_result, r, elapsed=12.4)
    assert "12.4s" in out


def test_format_result_list_data_as_bullets():
    r = make_result(data={"communities": ["Hak5", "Netgear"]})
    out = capture(format_result, r)
    assert "Hak5" in out
    assert "Netgear" in out


def test_format_result_dict_data_indented():
    r = make_result(data={"meta": {"key": "val"}})
    out = capture(format_result, r)
    assert "key" in out
    assert "val" in out


def test_format_result_pivots_grouped():
    r = make_result(pivots=[
        PivotEntity(type="domain", value="github.com"),
        PivotEntity(type="username", value="johndoe"),
    ])
    out = capture(format_result, r)
    assert "github.com" in out
    assert "johndoe" in out


def test_format_results_shows_summary_table():
    results = [make_result(), make_result(agent="domain", target="github.com")]
    buf = StringIO()
    console = Console(file=buf, no_color=True)
    format_results(results, console=console)
    out = buf.getvalue()
    assert "Agent" in out or "email" in out  # table header or row


def test_format_results_with_timings():
    results = [make_result()]
    buf = StringIO()
    console = Console(file=buf, no_color=True)
    from osint.core.run_context import RunContext
    ctx = RunContext()
    ctx._timings["email:foo@bar.com"] = 8.3
    format_results(results, console=console, context=ctx)
    out = buf.getvalue()
    assert "8.3" in out
```

- [ ] **Step 2: Run tests — expect failures**

```bash
pytest tests/output/test_rich_formatter.py -v
```
Expected: failures because `format_result` doesn't accept `console` or `elapsed` yet

- [ ] **Step 3: Rewrite `osint/output/rich_formatter.py`**

```python
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
                 No other fields are accessed.
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/output/test_rich_formatter.py -v
```
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add osint/output/rich_formatter.py tests/output/test_rich_formatter.py
git commit -m "feat: enhance rich_formatter with timing, improved data rendering, and summary table"
```

---

### Task 7: report_formatter (new)

**Files:**
- Create: `osint/output/report_formatter.py`
- Create: `tests/output/test_report_formatter.py`

- [ ] **Step 1: Write failing tests**

Create `tests/output/test_report_formatter.py`:
```python
from io import StringIO
from osint.output.report_formatter import format_results
from osint.core.result import OsintResult, PivotEntity
from osint.core.run_context import RunContext


def make_result(**kwargs):
    defaults = dict(
        agent="email", target="foo@bar.com", ai_used="gemini",
        success=True, data={"identity": "Nate", "tags": ["hardware", "rfid"]},
        pivots=[PivotEntity(type="domain", value="github.com")],
        raw_response="", error=None,
        timestamp="2026-03-13T00:00:00+00:00",
    )
    defaults.update(kwargs)
    return OsintResult(**defaults)


def capture_report(results, context=None) -> str:
    buf = StringIO()
    format_results(results, stream=buf, context=context)
    return buf.getvalue()


def test_report_has_header():
    out = capture_report([make_result()])
    assert "OSINT REPORT" in out


def test_report_has_target_summary():
    out = capture_report([make_result()])
    assert "foo@bar.com" in out


def test_report_has_agent_section():
    out = capture_report([make_result()])
    assert "EMAIL" in out.upper()


def test_report_shows_data_fields():
    out = capture_report([make_result()])
    assert "Nate" in out
    assert "hardware" in out


def test_report_shows_pivots():
    out = capture_report([make_result()])
    assert "github.com" in out


def test_report_shows_timeout_label():
    r = make_result(success=False, error="AgentError: TIMEOUT after 90.0s")
    out = capture_report([r])
    assert "[TIMEOUT]" in out


def test_report_timeout_shows_threshold_from_context():
    """context.timeout should appear in the [TIMEOUT] line."""
    r = make_result(success=False, error="AgentError: TIMEOUT after 45.0s")
    ctx = RunContext(timeout=45.0)
    out = capture_report([r], context=ctx)
    assert "45" in out


def test_report_shows_failed_label():
    r = make_result(success=False, error="AgentError: something went wrong")
    out = capture_report([r])
    assert "[FAILED]" in out


def test_report_shows_elapsed_with_context():
    ctx = RunContext()
    ctx._timings["email:foo@bar.com"] = 14.2
    out = capture_report([make_result()], context=ctx)
    assert "14.2" in out


def test_save_results_writes_file(tmp_path):
    from osint.output.report_formatter import save_results
    path = tmp_path / "report.txt"
    save_results([make_result()], str(path))
    assert path.exists()
    assert "OSINT REPORT" in path.read_text()
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/output/test_report_formatter.py -v
```
Expected: `ModuleNotFoundError: No module named 'osint.output.report_formatter'`

- [ ] **Step 3: Create `osint/output/report_formatter.py`**

```python
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
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/output/test_report_formatter.py -v
```
Expected: 10 passed

- [ ] **Step 5: Export from `osint/output/__init__.py`**

Replace contents of `osint/output/__init__.py` with:
```python
from osint.output import rich_formatter, json_formatter, report_formatter

__all__ = ["rich_formatter", "json_formatter", "report_formatter"]
```

- [ ] **Step 6: Commit**

```bash
git add osint/output/report_formatter.py osint/output/__init__.py tests/output/test_report_formatter.py
git commit -m "feat: add plain-text report_formatter with save support"
```

---

### Task 8: CLI — flags, Live setup, dispatch

**Files:**
- Modify: `osint/cli.py`

*CLI wiring is integration-level; tested via the smoke test in Task 9.*

- [ ] **Step 1: Rewrite `osint/cli.py`**

```python
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
        elapsed = context._timings.get(f"{agent_type}:{target}")
        rich_formatter.format_result(result, elapsed=elapsed)
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
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add osint/cli.py
git commit -m "feat: add --verbose, --timeout, --timeout-action, --output report to CLI"
```

---

### Task 9: Smoke test

*Manual validation — no real AI CLIs required. We mock the subprocess.*

- [ ] **Step 1: Verify help output**

```bash
osint --help
osint recon --help
osint email --help
```
Expected: `--verbose/-v`, `--timeout`, `--timeout-action`, `--output` all appear in `recon --help`. `--verbose/-v` appears in `email --help`.

- [ ] **Step 2: Run full test suite one final time**

```bash
pytest tests/ -v --tb=short
```
Expected: all tests pass

- [ ] **Step 3: Final commit (if any loose files)**

```bash
git status
# commit anything unstaged
```

---

## Quick Reference — Timing Key Format

Canonical key: `f"{agent_type}:{target}"` — e.g. `"email:foo@bar.com"`

Written in: `osint/agents/base.py` (`context._timings[key] = elapsed`)
Read in:
- `osint/orchestrator.py`: `context._timings.get(f"{at}:{t}")`
- `osint/cli.py` (`_run_agent`): `context._timings.get(f"{agent_type}:{target}")`
- `osint/output/rich_formatter.py`: `timings.get(f"{result.agent}:{result.target}")`
- `osint/output/report_formatter.py`: `timings.get(f"{result.agent}:{result.target}")`
