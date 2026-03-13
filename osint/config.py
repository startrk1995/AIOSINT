from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_path: str = "gemini"
    claude_path: str = "claude"
    codex_path: str = "codex"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
