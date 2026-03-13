# Design: Verbose Logging, Live Status, Timeouts, and Enhanced Output

**Date:** 2026-03-13
**Status:** Approved
**Scope:** osint Python package

---

## Overview

Add four capabilities to the OSINT meta-framework:

1. **Verbose logging** — `--verbose` / `-v` flag that shows prompts sent to AI CLIs and raw responses received
2. **Live terminal status** — per-agent spinner rows with elapsed time, updated in real time during any run
3. **Agent timeouts** — configurable per-agent timeout (default 90s) with warn or kill action
4. **Enhanced output** — richer Rich panels with timing + summary table; new `--output report` narrative format

All four are unified through a single `RunContext` dataclass threaded through the call stack.

---

## Architecture

### New file: `osint/core/run_context.py`

```python
@dataclass
class RunContext:
    verbose: bool = False
    timeout: float = 90.0          # seconds per agent subprocess
    timeout_action: str = "warn"   # "warn" | "kill"
    progress: Progress | None = None   # shared Rich Progress instance
    _timings: dict[str, float] = field(default_factory=dict)
```

- `verbose=True`: AIRunner prints the prompt and raw response via `progress.console.print()` in dim markup
- `timeout`: Default 90s. Rationale: Gemini/Claude typically finish in 15–45s; Codex script runs can reach 60–90s; beyond 90s is almost certainly hung
- `timeout_action`: controls live display label only — both modes kill and reap the subprocess (see Timeout Lifecycle). `"warn"` = yellow row, BFS continues with the timeout error result. `"kill"` = red row, same behavior. The distinction is intentionally cosmetic for this iteration; both modes record a timeout `AgentError` and allow the BFS to continue. This is stated explicitly so the implementer does not invent additional branching.
- Single-agent commands (not `recon`) always use the default `timeout=90.0` and `timeout_action="warn"`. These are not exposed as CLI flags on single-agent commands. The `RunContext` constructed in `_run_agent` always uses these defaults.

---

### Modified: `osint/core/ai_runner.py`

`AIRunner.run()` gains an optional `context: RunContext | None` parameter.

**Timeout lifecycle — both modes:**

```python
process = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
try:
    stdout, stderr = await asyncio.wait_for(
        process.communicate(), timeout=context.timeout
    )
except asyncio.TimeoutError:
    process.kill()
    await process.communicate()   # reap the zombie; must not be omitted
    if context.timeout_action == "kill":
        raise AgentError(f"TIMEOUT after {context.timeout}s")
    else:  # "warn"
        # Row turns yellow in Live display; result recorded as timeout error
        raise AgentError(f"TIMEOUT after {context.timeout}s")
```

Both `warn` and `kill` raise `AgentError` after killing and reaping the subprocess. The difference is surfaced in the live display row color/label, not in whether the process is killed. In both cases the OS process is fully terminated before Python moves on — no dangling processes or resource leaks.

**Invariant:** When `context.verbose=True`, `context.progress` must be non-None. `AIRunner` enforces this with a guard: if `context.verbose` is True but `context.progress` is None, fall back to `Console().print(...)` rather than raising `AttributeError`.

If `context.verbose`: before launching the subprocess, call `context.progress.console.print(prompt, style="dim cyan")`. After receiving stdout, call `context.progress.console.print(stdout, style="dim white")`. This routes through the single console that owns the `Live` context, preventing display corruption.

---

### Modified: `osint/agents/base.py`

`make_run_fn` returns `run(target: str, context: RunContext | None = None)`.

```python
async def run(target: str, context: RunContext | None = None) -> OsintResult:
    ...
    raw = await AIRunner().run(ai_cli, prompt, context=context)
    ...
```

Before calling `AIRunner`, if `context.progress` is set, update the agent's progress task row to "running." After completion (success or error), mark it done and record elapsed time in `context._timings[f"{agent_type}:{target}"]`.

The timing key format `f"{agent_type}:{target}"` (e.g. `"email:foo@bar.com"`) is the canonical key used throughout — in `base.py` when writing, and in callers when reading.

---

### Modified: `osint/agents/__init__.py`

Update the registry type annotation from:
```python
dict[str, tuple[Callable[[str], Awaitable[OsintResult]], str]]
```
to:
```python
dict[str, tuple[Callable[..., Awaitable[OsintResult]], str]]
```

---

### Modified: `osint/orchestrator.py`

`OSINTOrchestrator.run()` gains `context: RunContext | None = None`.

The BFS task dispatch becomes:

```python
tasks = []
task_items = []
for at, t, depth in level_items:
    if at in AGENT_REGISTRY:
        run_fn, _ = AGENT_REGISTRY[at]
        tasks.append(run_fn(t, context=context))   # <-- pass context
        task_items.append((at, t, depth))
```

The orchestrator opens the `Live` context before entering the BFS loop and closes it after all levels complete. All result panel printing happens **after** the `Live` context exits — never inside it.

```python
with Live(progress, console=shared_console, refresh_per_second=4):
    # BFS loop here — no console.print() inside
    ...

# Live context has exited; now safe to print panels
for (at, t, _depth), result in zip(task_items, level_results):
    rich_formatter.format_result(result, elapsed=context._timings.get(f"{at}:{t}"))
```

---

### Modified: `osint/cli.py`

**Flags added to all commands:**
- `--verbose / -v`: `bool = typer.Option(False, "--verbose", "-v")`

**Flags added to `recon` only:**
- `--timeout FLOAT` (default 90.0)
- `--timeout-action [warn|kill]` (default "warn")
- `--output` now accepts `"rich"`, `"json"`, or `"report"`

**Updated validation and dispatch in `recon`:**

```python
if output not in ("rich", "json", "report"):
    console.print(f"[red]Error: Invalid output format '{output}'. Choose 'rich', 'json', or 'report'[/red]")
    raise typer.Exit(code=1)

# After run completes:
if output == "rich":
    # panels already printed by orchestrator after Live exits
    pass
elif output == "json":
    console.print(json_formatter.format_results(results))
elif output == "report":
    report_formatter.format_results(results, context=context)
```

**Single-agent commands** (`_run_agent`):

```python
def _run_agent(agent_type: str, target: str, verbose: bool = False) -> None:
    _check_binaries()
    shared_console = Console()
    progress = Progress(...)
    context = RunContext(verbose=verbose, progress=progress)

    with Live(progress, console=shared_console, refresh_per_second=4):
        result = asyncio.run(run_fn(target, context=context))

    # Live has exited — safe to print
    # Timing key uses agent_type and target, same format as base.py writes
    rich_formatter.format_result(result, elapsed=context._timings.get(f"{agent_type}:{target}"))
```

The `Live` context manager is opened synchronously in `_run_agent` before `asyncio.run()`. `RunContext.progress` is populated before the coroutine is called.

**Phone number normalization** moves into the `phone` agent's `run()` closure (not `cli.py`), so it applies regardless of whether the phone target arrives from the CLI or from a BFS pivot:

```python
# In osint/agents/phone.py (expanded from the 6-line wrapper pattern)
from osint.agents.base import make_run_fn

AGENT_TYPE = "phone"
AI_CLI = "claude"

_base_run = make_run_fn(AGENT_TYPE, AI_CLI)   # the standard factory closure

async def run(target: str, context=None) -> OsintResult:
    target = normalize_phone(target)
    return await _base_run(target, context=context)
```

`normalize_phone()` handles:
- `+1-555-999-0202` → `555-999-0202`
- `1-555-999-0202` → `555-999-0202`
- `5559990202` → `555-999-0202`
- `(555) 999-0202` → `555-999-0202`
- `555-999-0202` → unchanged

Non-US numbers (more than 10 significant digits after stripping country code) are passed through unchanged with a verbose log note.

---

### Output sequencing rule

During any run with a `Live` display active:
- **All** output goes through `context.progress.console` (verbose logs, warnings)
- `console.print()` at module level in `rich_formatter.py` must **not** be called while `Live` is active
- Result panels and the summary table are printed after `Live.__exit__()` returns
- The `rich_formatter` module-level `console` is replaced with a parameter: `format_result(result, console=None, elapsed=None)` where `console` defaults to a fresh `Console()` if not provided

---

### Modified: `osint/output/rich_formatter.py`

- `format_result(result, console=None, elapsed=None)` — `console` param prevents module-level console conflicts
- Panel title includes elapsed: `[email] → foo@bar.com  (12.4s)`
- Data field rendering by type:
  - `list`: bullet points
  - `dict`: indented key/value
  - scalar: inline
- Pivot section groups pivots by type with colored labels
- `format_results(results, context=None)` prints a Rich `Table` after all panels:
  - Columns: Agent | Target | Status | Time | Pivots
  - From `context`, reads only `context._timings` (a `dict[str, float]`) to populate the Time column. No other fields are accessed. If `context` is None, the Time column is omitted.

---

### New: `osint/output/report_formatter.py`

Plain-text narrative report, no Rich markup. Safe to redirect to file.

```
════════════════════════════════════════
  OSINT REPORT  —  <target>
  Generated: YYYY-MM-DD HH:MM UTC
════════════════════════════════════════

TARGET SUMMARY
  Seed: <target>  |  Depth: N  |  Agents: N  |  Duration: Xm Xs

── EMAIL ────────────────────────────────
  Identity ......... Nate
  GitHub ........... github.com/startrk1995
  Communities ...... Hak5 Forums, Netgear Community (+2 more)

  Pivots → domain: github.com
           username: startrk1995

[TIMEOUT] username: startrk1995 — exceeded 90s
[FAILED]  phone: 555-999-0202 — AgentError: ...
```

- `format_results(results, context=None)` → prints to stdout
  - From `context`, reads: `context._timings` (for per-agent elapsed time) and `context.timeout` (for the `[TIMEOUT]` threshold display). No other fields accessed. If `context` is None, elapsed time and timeout labels are omitted.
- `save_results(results, path, context=None)` → writes `.txt` file using the same data as `format_results`

---

## Live Status Display

```
 Running OSINT Recon — depth 2
 ─────────────────────────────────────────────────────────────
 ⠸ [email]    startrk1995@gmail.com       gemini    0:00:12
 ✓ [domain]   github.com                  gemini    0:00:08  done
 ⠼ [username] startrk1995                 codex     0:00:34
 ✗ [phone]    555-999-0202                claude    0:01:31  TIMEOUT
```

- Single-agent commands show a single-row live display
- `--verbose` adds scrolling log pane via `progress.console.print()` — same console as Live
- Timeout row turns yellow and appends `TIMEOUT`
- All output sequenced: Live runs during execution, exits before panels are printed

---

## Timeout Defaults by Agent

| Agent | AI CLI | Expected range | Default timeout |
|-------|--------|---------------|-----------------|
| email | gemini | 10–40s | 90s |
| domain | gemini | 10–40s | 90s |
| phone | claude | 10–30s | 90s |
| person | claude | 10–30s | 90s |
| username | codex | 20–60s | 90s |
| social | codex | 20–60s | 90s |
| image | codex | 15–60s | 90s |
| location | codex | 15–60s | 90s |

Single global timeout (default 90s). Per-agent overrides not in scope for this iteration.

---

## Files Changed

| File | Change |
|------|--------|
| `osint/core/run_context.py` | **New** — RunContext dataclass |
| `osint/core/__init__.py` | Export RunContext |
| `osint/core/ai_runner.py` | context param, subprocess timeout+kill lifecycle, verbose logging |
| `osint/agents/base.py` | Thread context through run_fn; update progress row |
| `osint/agents/phone.py` | Expanded from 6-line wrapper to include normalize_phone() |
| `osint/agents/__init__.py` | Update AGENT_REGISTRY type annotation |
| `osint/orchestrator.py` | Thread context, Live display, output sequencing |
| `osint/cli.py` | --verbose, --timeout, --timeout-action, --output report, Live setup in _run_agent |
| `osint/output/rich_formatter.py` | console param, timing headers, data rendering, summary table |
| `osint/output/report_formatter.py` | **New** — plain text narrative report |
| `osint/output/__init__.py` | Export report_formatter |

---

## Out of Scope

- Per-agent timeout overrides
- Log file output (`--log-file`)
- Retry on timeout
- Structured logging (JSON logs)
- Non-US phone normalization beyond pass-through
