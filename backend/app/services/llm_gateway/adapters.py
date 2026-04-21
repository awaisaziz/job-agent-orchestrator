"""Provider adapters for normalized LLM text generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.services.llm_gateway.registry import ModelConfig
from app.services.llm_gateway.types import LLMGenerateRequest, LLMGenerateResponse, LLMUsage


class LLMAdapter(Protocol):
    def generate_text(self, request: LLMGenerateRequest, model_config: ModelConfig) -> LLMGenerateResponse: ...


@dataclass(slots=True)
class OpenAIAdapter:
    api_key: str
    base_url: str = "https://api.openai.com/v1/chat/completions"

    def generate_text(self, request: LLMGenerateRequest, model_config: ModelConfig) -> LLMGenerateResponse:
        payload = {
            "model": model_config.api_model,
            "messages": _to_chat_messages(request),
            "temperature": request.temperature if request.temperature is not None else model_config.temperature,
            "max_tokens": request.max_tokens if request.max_tokens is not None else model_config.max_tokens,
        }
        data = _post_json(self.base_url, payload, headers={"Authorization": f"Bearer {self.api_key}"})
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return LLMGenerateResponse(
            provider="openai",
            model_name=model_config.api_model,
            output_text=str(message.get("content") or "").strip(),
            finish_reason=choice.get("finish_reason"),
            usage=LLMUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            ),
            raw_response=data,
        )


@dataclass(slots=True)
class AnthropicAdapter:
    api_key: str
    base_url: str = "https://api.anthropic.com/v1/messages"

    def generate_text(self, request: LLMGenerateRequest, model_config: ModelConfig) -> LLMGenerateResponse:
        payload = {
            "model": model_config.api_model,
            "system": request.system_prompt or "You are a helpful assistant.",
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature if request.temperature is not None else model_config.temperature,
            "max_tokens": request.max_tokens if request.max_tokens is not None else model_config.max_tokens,
        }
        data = _post_json(
            self.base_url,
            payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        parts = data.get("content") or []
        first_text_block = next((part for part in parts if part.get("type") == "text"), {})
        usage = data.get("usage") or {}
        return LLMGenerateResponse(
            provider="anthropic",
            model_name=model_config.api_model,
            output_text=str(first_text_block.get("text") or "").strip(),
            finish_reason=data.get("stop_reason"),
            usage=LLMUsage(
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                total_tokens=(usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0),
            ),
            raw_response=data,
        )


@dataclass(slots=True)
class GrokAdapter:
    api_key: str
    base_url: str = "https://api.x.ai/v1/chat/completions"

    def generate_text(self, request: LLMGenerateRequest, model_config: ModelConfig) -> LLMGenerateResponse:
        payload = {
            "model": model_config.api_model,
            "messages": _to_chat_messages(request),
            "temperature": request.temperature if request.temperature is not None else model_config.temperature,
            "max_tokens": request.max_tokens if request.max_tokens is not None else model_config.max_tokens,
        }
        data = _post_json(self.base_url, payload, headers={"Authorization": f"Bearer {self.api_key}"})
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        return LLMGenerateResponse(
            provider="grok",
            model_name=model_config.api_model,
            output_text=str(message.get("content") or "").strip(),
            finish_reason=choice.get("finish_reason"),
            usage=LLMUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
            ),
            raw_response=data,
        )


def _to_chat_messages(request: LLMGenerateRequest) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if request.system_prompt:
        messages.append({"role": "system", "content": request.system_prompt})
    messages.append({"role": "user", "content": request.prompt})
    return messages


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    merged_headers = {
        "Content-Type": "application/json",
        **headers,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(url=url, data=body, headers=merged_headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM provider request failed ({exc.code}): {response_body}") from exc
