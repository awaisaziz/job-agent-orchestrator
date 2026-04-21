"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Job Agent Orchestrator"
    environment: str = "development"


settings = Settings()
