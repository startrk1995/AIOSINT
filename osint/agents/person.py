"""OSINT person research agent using Claude CLI."""
from osint.agents.base import make_run_fn

AGENT_TYPE = "person"
AI_CLI = "claude"

run = make_run_fn(AGENT_TYPE, AI_CLI)
