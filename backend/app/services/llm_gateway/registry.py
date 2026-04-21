"""Model registry for routing model names to providers and defaults."""

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ModelConfig:
    provider: str
    api_model: str
    temperature: float
    max_tokens: int


MODEL_REGISTRY: dict[str, ModelConfig] = {
    "gpt-4.1-mini": ModelConfig(provider="openai", api_model="gpt-4.1-mini", temperature=0.2, max_tokens=800),
    "gpt-4o-mini": ModelConfig(provider="openai", api_model="gpt-4o-mini", temperature=0.2, max_tokens=800),
    "claude-3-5-sonnet": ModelConfig(
        provider="anthropic", api_model="claude-3-5-sonnet-latest", temperature=0.2, max_tokens=800
    ),
    "claude-3-7-sonnet": ModelConfig(
        provider="anthropic", api_model="claude-3-7-sonnet-latest", temperature=0.2, max_tokens=800
    ),
    "grok-3-mini": ModelConfig(provider="grok", api_model="grok-3-mini", temperature=0.2, max_tokens=800),
    "grok-3": ModelConfig(provider="grok", api_model="grok-3", temperature=0.2, max_tokens=800),
}


DEFAULT_MODEL_NAME = "gpt-4.1-mini"
