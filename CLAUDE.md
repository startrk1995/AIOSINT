# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based OSINT meta-framework where each agent delegates research to a specific AI CLI tool (Gemini, Claude, or Codex) via subprocess. The orchestrator chains agents together using pivots extracted from AI responses.

No direct API calls to external services — the AI CLIs handle all research via their native capabilities (Gemini web search, Codex code execution, Claude reasoning).

## Setup

```bash
pip install -e .
cp .env.example .env   # set CLI binary paths if not in PATH
```

Requires AI CLI binaries installed and available in PATH:
- `gemini` — Google Gemini CLI
- `claude` — Claude Code CLI
- `codex` — OpenAI Codex CLI

## Architecture

```
osint/
├── cli.py                   # Typer CLI entry point (osint command)
├── config.py                # pydantic-settings: CLI binary paths
├── orchestrator.py          # BFS pivot engine
├── core/
│   ├── result.py            # OsintResult + PivotEntity Pydantic models
│   ├── ai_runner.py         # async subprocess wrapper (gemini/claude/codex)
│   ├── prompt_builder.py    # per-agent JSON-schema prompts + parse_json_response
│   └── cdn_filter.py        # CDN/VPN CIDR filter (is_cdn_ip) — blocks CDN pivots
├── agents/
│   ├── base.py              # make_run_fn factory (shared agent logic)
│   ├── __init__.py          # AGENT_REGISTRY + AI assignment map
│   ├── email.py             # → Gemini
│   ├── domain.py            # → Gemini
│   ├── phone.py             # → Claude
│   ├── person.py            # → Claude
│   ├── username.py          # → Codex
│   ├── social.py            # → Codex
│   ├── image.py             # → Codex
│   ├── location.py          # → Codex
│   └── ip.py                # → Gemini
└── output/
    ├── rich_formatter.py    # color-coded Rich panels
    └── json_formatter.py    # JSON serializer
```

## AI Assignment by Agent

| Agent | AI CLI | Rationale |
|-------|--------|-----------|
| email | Gemini | Google-indexed breach data, web search |
| domain | Gemini | WHOIS, DNS, Google-indexed domain intel |
| phone | Claude | Structured reasoning over carrier/region/validation |
| person | Claude | Connects public records via reasoning |
| username | Codex | Writes + runs Python to check platforms |
| social | Codex | Scripts cross-platform profile lookups |
| image | Codex | Executes EXIF parsing, reverse search scripts |
| location | Codex | Scripts geocoding / address reverse lookup |
| ip | Gemini | Web search for geolocation, ASN, reputation, blacklists |

## Key Design Decisions

- **PivotEntity.type** (not `agent_type`) — matches the JSON schema the AI returns
- **AIRunner** reads binary paths from `settings` (not hardcoded) — configure via `.env`
- **parse_json_response** uses brace-depth scanning (not greedy regex) — handles AI prose around JSON
- **make_run_fn factory** (`agents/base.py`) — all 9 agent files are 6-line wrappers around this
- **CDN IP filtering** (`core/cdn_filter.py`) — two-layer defense: AI prompt asks to exclude CDN IPs, orchestrator also filters via `is_cdn_ip()` before queuing pivots
- **IP agent is primary-only** — `PIVOT_HINTS["ip"] = ""` so the AI returns no further pivots from IP lookups; prevents cascading
- **Orchestrator BFS** uses `task_items` (not `level_items`) in the zip — prevents misalignment when unknown pivot types are filtered out

## Testing

```bash
pip install -e ".[dev]"
pytest                          # all tests
pytest tests/test_cli_ip.py     # single test file
pytest -x                       # stop on first failure
pytest -s                       # show subprocess stdout (useful for AI runner tests)
```

Tests use `pytest-asyncio` with `asyncio_mode = "auto"` — no `@pytest.mark.asyncio` needed.

## CLI Usage

```bash
# Single-agent commands
osint email foo@bar.com
osint phone "+1-555-0100"
osint domain example.com
osint username johndoe
osint name "John Doe"
osint location "123 Main St, New York"
osint image /path/to/photo.jpg
osint social johndoe
osint ip 1.2.3.4

# Full auto-pivot recon
osint recon foo@bar.com --depth 2 --output json --save results.json
```

## Adding a New Agent

1. Create `osint/agents/myagent.py`:
   ```python
   from osint.agents.base import make_run_fn
   AGENT_TYPE = "myagent"
   AI_CLI = "gemini"  # or "claude" / "codex"
   run = make_run_fn(AGENT_TYPE, AI_CLI)
   ```
2. Add to `AGENT_REGISTRY` in `osint/agents/__init__.py`
3. Add a `RESEARCH_TASKS` and `PIVOT_HINTS` entry in `osint/core/prompt_builder.py`
