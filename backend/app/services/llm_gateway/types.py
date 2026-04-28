"""Normalized request/response types for provider-agnostic text generation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class LLMGenerateRequest:
    """Normalized text generation request consumed by gateway adapters."""

    model_name: str
    prompt: str
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class LLMUsage:
    """Usage token accounting normalized across providers."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(slots=True, frozen=True)
class LLMGenerateResponse:
    """Normalized text generation response returned by gateway."""

    provider: str
    model_name: str
    output_text: str
    finish_reason: str | None = None
    usage: LLMUsage = LLMUsage()
    raw_response: dict[str, Any] = field(default_factory=dict)
