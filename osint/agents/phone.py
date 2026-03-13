"""OSINT phone research agent using Claude CLI."""
from osint.agents.base import make_run_fn

AGENT_TYPE = "phone"
AI_CLI = "claude"

run = make_run_fn(AGENT_TYPE, AI_CLI)
