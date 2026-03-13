"""OSINT domain research agent using Gemini CLI."""
from osint.agents.base import make_run_fn

AGENT_TYPE = "domain"
AI_CLI = "gemini"

run = make_run_fn(AGENT_TYPE, AI_CLI)
