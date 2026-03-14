"""Agent registry for the OSINT framework."""
from osint.agents import email, domain, phone, person, username, social, image, location, ip
from typing import Callable, Awaitable
from osint.core import OsintResult

# Map of agent_type -> (run_function, ai_cli)
AGENT_REGISTRY: dict[str, tuple[Callable[..., Awaitable[OsintResult]], str]] = {
    "email":    (email.run,    "gemini"),
    "domain":   (domain.run,   "gemini"),
    "phone":    (phone.run,    "claude"),
    "person":   (person.run,   "claude"),
    "username": (username.run, "codex"),
    "social":   (social.run,   "codex"),
    "image":    (image.run,    "codex"),
    "location": (location.run, "codex"),
    "ip":       (ip.run,       "gemini"),
}
