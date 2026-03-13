"""OSINT username research agent using Codex CLI."""
from osint.agents.base import make_run_fn

AGENT_TYPE = "username"
AI_CLI = "codex"

run = make_run_fn(AGENT_TYPE, AI_CLI)
