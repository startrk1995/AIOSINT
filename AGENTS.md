# AGENTS.md

Guidance for AI coding agents (Codex, OpenAI o-series, etc.) working in this repository.

## Project Overview

Python OSINT meta-framework. Each of the 8 research agents delegates to a specific AI CLI subprocess (Gemini, Claude, or Codex). A BFS orchestrator chains agents by extracting pivot entities from results.

## Setup

```bash
pip install -e .
```

## Repository Structure

```
osint/
├── cli.py              # Entry point: Typer CLI, `osint` command
├── config.py           # Settings (binary paths), reads from .env
├── orchestrator.py     # BFS pivot chaining engine
├── core/
│   ├── result.py       # OsintResult, PivotEntity (Pydantic models)
│   ├── ai_runner.py    # AIRunner: async subprocess dispatch
│   └── prompt_builder.py  # PromptBuilder + parse_json_response
├── agents/
│   ├── base.py         # make_run_fn(agent_type, ai_cli) factory
│   ├── __init__.py     # AGENT_REGISTRY
│   └── *.py            # 8 agent files (6 lines each)
└── output/
    ├── rich_formatter.py
    └── json_formatter.py
```

## Critical Implementation Details

### PivotEntity field name
`PivotEntity.type` (not `agent_type`). This matches the JSON schema returned by AI CLIs.

### Agent factory pattern
All agents use `make_run_fn` from `agents/base.py`. Do not duplicate the run logic.

### Orchestrator zip alignment
The orchestrator uses `task_items` (parallel to `tasks`) in `zip(task_items, level_results)`, not `level_items`. This prevents result misalignment when unknown pivot types are filtered out.

### JSON parsing
`parse_json_response` uses brace-depth scanning. Do not replace with regex — it handles `}` inside string values correctly.

### Config
Binary paths are read from `settings` at runtime. `AIRunner._get_commands()` calls `settings.gemini_path` etc. Do not hardcode binary names.

## Common Tasks

### Add a new agent
1. `osint/agents/newagent.py` — 6 lines using `make_run_fn`
2. Add entry to `AGENT_REGISTRY` in `osint/agents/__init__.py`
3. Add `RESEARCH_TASKS["newagent"]`, `PIVOT_HINTS["newagent"]` in `osint/core/prompt_builder.py`

### Run the CLI
```bash
osint email test@example.com
osint recon test@example.com --depth 2
```

### Test imports
```bash
python3 -c "from osint.agents import AGENT_REGISTRY; from osint.orchestrator import OSINTOrchestrator; print('OK')"
```
