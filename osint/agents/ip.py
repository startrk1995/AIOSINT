"""IP address OSINT agent — delegates to Gemini for IP intelligence."""
from osint.agents.base import make_run_fn

AGENT_TYPE = "ip"
AI_CLI = "gemini"
run = make_run_fn(AGENT_TYPE, AI_CLI)
