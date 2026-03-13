from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_path: str = "gemini"
    claude_path: str = "claude"
    codex_path: str = "codex"

    class Config:
        env_file = ".env"


settings = Settings()
