"""Model-based router for LLM provider adapters."""

from app.core.config import settings
from app.services.llm_gateway.adapters import AnthropicAdapter, GrokAdapter, LLMAdapter, OpenAIAdapter
from app.services.llm_gateway.registry import MODEL_REGISTRY, ModelConfig
from app.services.llm_gateway.types import LLMGenerateRequest, LLMGenerateResponse


class LLMGatewayError(RuntimeError):
    """Base gateway error."""


class UnknownModelError(LLMGatewayError):
    """Raised when no model registry entry exists for a model name."""


class MissingAPIKeyError(LLMGatewayError):
    """Raised when the selected provider has no configured API key."""


def generate_text(request: LLMGenerateRequest) -> LLMGenerateResponse:
    model_name = request.model_name or settings.llm_default_model
    model_config = _resolve_model_config(model_name)
    adapter = _resolve_adapter(model_config)
    return adapter.generate_text(request=request, model_config=model_config)


def _resolve_model_config(model_name: str) -> ModelConfig:
    if model_name not in settings.llm_enabled_models:
        raise UnknownModelError(
            f"Model '{model_name}' is not enabled. Enabled models: {', '.join(sorted(settings.llm_enabled_models))}"
        )
    model_config = MODEL_REGISTRY.get(model_name)
    if model_config is None:
        raise UnknownModelError(f"Unknown model_name '{model_name}'. Known models: {', '.join(sorted(MODEL_REGISTRY))}")
    return model_config


def _resolve_adapter(model_config: ModelConfig) -> LLMAdapter:
    if model_config.provider == "openai":
        if not settings.openai_api_key:
            raise MissingAPIKeyError("OPENAI_API_KEY is not configured")
        return OpenAIAdapter(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or OpenAIAdapter.base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if model_config.provider == "anthropic":
        if not settings.anthropic_api_key:
            raise MissingAPIKeyError("ANTHROPIC_API_KEY is not configured")
        return AnthropicAdapter(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url or AnthropicAdapter.base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if model_config.provider == "grok":
        if not settings.grok_api_key:
            raise MissingAPIKeyError("GROK_API_KEY is not configured")
        return GrokAdapter(
            api_key=settings.grok_api_key,
            base_url=settings.grok_base_url or GrokAdapter.base_url,
            timeout_seconds=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    raise UnknownModelError(f"Unknown provider '{model_config.provider}'")
