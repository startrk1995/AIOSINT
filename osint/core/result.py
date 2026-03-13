from pydantic import BaseModel
from typing import Any


class PivotEntity(BaseModel):
    type: str   # "domain", "username", "email", etc.
    value: str


class OsintResult(BaseModel):
    agent: str
    target: str
    ai_used: str           # "gemini" | "claude" | "codex"
    success: bool
    data: dict[str, Any]
    pivots: list[PivotEntity] = []
    raw_response: str = ""  # full AI CLI output for debugging
    error: str | None = None
    timestamp: str
