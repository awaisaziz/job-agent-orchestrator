"""Application configuration."""

from __future__ import annotations

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.llm_gateway.registry import DEFAULT_MODEL_NAME, MODEL_REGISTRY


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Job Agent Orchestrator"
    environment: str = "development"

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    grok_api_key: str | None = Field(default=None, alias="GROK_API_KEY")

    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    anthropic_base_url: str | None = Field(default=None, alias="ANTHROPIC_BASE_URL")
    grok_base_url: str | None = Field(default=None, alias="GROK_BASE_URL")

    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS", gt=0)
    llm_max_retries: int = Field(default=1, alias="LLM_MAX_RETRIES", ge=0)

    llm_default_model: str = Field(default=DEFAULT_MODEL_NAME, alias="LLM_DEFAULT_MODEL")
    llm_enabled_models: list[str] = Field(default_factory=lambda: sorted(MODEL_REGISTRY), alias="LLM_ENABLED_MODELS")

    gmail_readonly_scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/gmail.readonly",
            "openid",
            "email",
            "profile",
        ],
        alias="GMAIL_READONLY_SCOPES",
    )
    email_token_encryption_key: str = Field(default="dev-email-token-key", alias="EMAIL_TOKEN_ENCRYPTION_KEY")
    email_sync_min_interval_seconds: int = Field(default=60, alias="EMAIL_SYNC_MIN_INTERVAL_SECONDS", ge=1)
    email_sync_max_messages: int = Field(default=100, alias="EMAIL_SYNC_MAX_MESSAGES", ge=1, le=500)

    @model_validator(mode="before")
    @classmethod
    def _parse_enabled_models(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values
        enabled_models = values.get("LLM_ENABLED_MODELS", values.get("llm_enabled_models"))
        if isinstance(enabled_models, str):
            values["LLM_ENABLED_MODELS"] = [model.strip() for model in enabled_models.split(",") if model.strip()]

        gmail_scopes = values.get("GMAIL_READONLY_SCOPES", values.get("gmail_readonly_scopes"))
        if isinstance(gmail_scopes, str):
            values["GMAIL_READONLY_SCOPES"] = [scope.strip() for scope in gmail_scopes.split(",") if scope.strip()]
        return values

    @model_validator(mode="after")
    def _validate_model_configuration(self) -> "Settings":
        unknown_models = sorted(set(self.llm_enabled_models) - set(MODEL_REGISTRY))
        if unknown_models:
            raise ValueError(f"LLM_ENABLED_MODELS contains unknown model(s): {', '.join(unknown_models)}")

        if self.llm_default_model not in MODEL_REGISTRY:
            raise ValueError(
                f"LLM_DEFAULT_MODEL '{self.llm_default_model}' is unknown. "
                f"Known models: {', '.join(sorted(MODEL_REGISTRY))}"
            )

        if self.llm_default_model not in self.llm_enabled_models:
            raise ValueError("LLM_DEFAULT_MODEL must be included in LLM_ENABLED_MODELS")

        provider = MODEL_REGISTRY[self.llm_default_model].provider
        provider_keys: dict[str, str | None] = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "grok": self.grok_api_key,
        }
        if not provider_keys.get(provider):
            raise ValueError(
                f"LLM_DEFAULT_MODEL '{self.llm_default_model}' requires {provider.upper()}_API_KEY to be configured"
            )

        return self


settings = Settings()
