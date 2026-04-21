"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Job Agent Orchestrator"
    environment: str = "development"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    grok_api_key: str | None = None


settings = Settings()
