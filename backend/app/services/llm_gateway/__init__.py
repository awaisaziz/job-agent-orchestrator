"""LLM gateway service exports."""

from app.services.llm_gateway.registry import DEFAULT_MODEL_NAME, MODEL_REGISTRY
from app.services.llm_gateway.types import LLMGenerateRequest, LLMGenerateResponse

__all__ = [
    "DEFAULT_MODEL_NAME",
    "MODEL_REGISTRY",
    "LLMGatewayError",
    "MissingAPIKeyError",
    "UnknownModelError",
    "LLMGenerateRequest",
    "LLMGenerateResponse",
    "generate_text",
]


def __getattr__(name: str):
    if name in {"LLMGatewayError", "MissingAPIKeyError", "UnknownModelError", "generate_text"}:
        from app.services.llm_gateway.service import (
            LLMGatewayError,
            MissingAPIKeyError,
            UnknownModelError,
            generate_text,
        )

        exports = {
            "LLMGatewayError": LLMGatewayError,
            "MissingAPIKeyError": MissingAPIKeyError,
            "UnknownModelError": UnknownModelError,
            "generate_text": generate_text,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
