"""Model-based router for LLM provider adapters."""

from app.core.config import settings
from app.services.llm_gateway.adapters import AnthropicAdapter, GrokAdapter, LLMAdapter, OpenAIAdapter
from app.services.llm_gateway.registry import DEFAULT_MODEL_NAME, MODEL_REGISTRY, ModelConfig
from app.services.llm_gateway.types import LLMGenerateRequest, LLMGenerateResponse


class LLMGatewayError(RuntimeError):
    """Base gateway error."""


class UnknownModelError(LLMGatewayError):
    """Raised when no model registry entry exists for a model name."""


class MissingAPIKeyError(LLMGatewayError):
    """Raised when the selected provider has no configured API key."""


def generate_text(request: LLMGenerateRequest) -> LLMGenerateResponse:
    model_name = request.model_name or DEFAULT_MODEL_NAME
    model_config = _resolve_model_config(model_name)
    adapter = _resolve_adapter(model_config)
    return adapter.generate_text(request=request, model_config=model_config)


def _resolve_model_config(model_name: str) -> ModelConfig:
    model_config = MODEL_REGISTRY.get(model_name)
    if model_config is None:
        raise UnknownModelError(f"Unknown model_name '{model_name}'. Known models: {', '.join(sorted(MODEL_REGISTRY))}")
    return model_config


def _resolve_adapter(model_config: ModelConfig) -> LLMAdapter:
    if model_config.provider == "openai":
        if not settings.openai_api_key:
            raise MissingAPIKeyError("OPENAI_API_KEY is not configured")
        return OpenAIAdapter(api_key=settings.openai_api_key)
    if model_config.provider == "anthropic":
        if not settings.anthropic_api_key:
            raise MissingAPIKeyError("ANTHROPIC_API_KEY is not configured")
        return AnthropicAdapter(api_key=settings.anthropic_api_key)
    if model_config.provider == "grok":
        if not settings.grok_api_key:
            raise MissingAPIKeyError("GROK_API_KEY is not configured")
        return GrokAdapter(api_key=settings.grok_api_key)
    raise UnknownModelError(f"Unknown provider '{model_config.provider}'")
