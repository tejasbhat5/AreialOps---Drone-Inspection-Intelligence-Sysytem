from __future__ import annotations

import json
from contextlib import suppress
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.schemas.assistant import AssistantResponseType


class ModelProviderError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


class ModelToolCall(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class ModelSynthesis(BaseModel):
    response_type: AssistantResponseType
    answer: str = Field(min_length=1, max_length=4_000)


class ModelStep(BaseModel):
    output_items: list[dict[str, Any]]
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    synthesis: ModelSynthesis | None = None


SYNTHESIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "response_type": {
            "type": "string",
            "enum": [item.value for item in AssistantResponseType],
        },
        "answer": {"type": "string"},
    },
    "required": ["response_type", "answer"],
    "additionalProperties": False,
}


class OpenAIResponsesProvider:
    """Small Responses API adapter; application orchestration remains provider-neutral."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = client or httpx.Client(
            base_url="https://api.openai.com/v1",
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def label(self) -> str:
        return f"openai:{self.model}"

    def respond(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> ModelStep:
        tools = [
            {
                "type": "function",
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
                "strict": False,
            }
            for schema in tool_schemas
        ]
        try:
            response = self.client.post(
                "/responses",
                json={
                    "model": self.model,
                    "instructions": instructions,
                    "input": input_items,
                    "tools": tools,
                    "tool_choice": "auto",
                    "parallel_tool_calls": False,
                    "store": False,
                    "max_output_tokens": self.max_output_tokens,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "aerialops_answer",
                            "strict": True,
                            "schema": SYNTHESIS_SCHEMA,
                        }
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exception:
            raise ModelProviderError(
                "model_timeout", "The AI provider timed out; local planning will be used."
            ) from exception
        except httpx.HTTPStatusError as exception:
            status_code = exception.response.status_code
            provider_code = ""
            with suppress(ValueError):
                provider_code = exception.response.json().get("error", {}).get("code", "")
            if status_code in {401, 403}:
                code = "model_authentication_failed"
            elif status_code == 429 and provider_code == "insufficient_quota":
                code = "model_quota_exceeded"
            elif status_code == 429:
                code = "model_rate_limited"
            else:
                code = "model_provider_failed"
            raise ModelProviderError(
                code, "The AI provider is unavailable; local planning will be used."
            ) from exception
        except (httpx.HTTPError, ValueError) as exception:
            raise ModelProviderError(
                "model_provider_failed",
                "The AI provider returned an invalid response; local planning will be used.",
            ) from exception

        output_items = payload.get("output")
        if not isinstance(output_items, list):
            raise ModelProviderError(
                "malformed_model_output",
                "The AI provider returned an invalid response; local planning will be used.",
            )

        calls: list[ModelToolCall] = []
        for item in output_items:
            if not isinstance(item, dict) or item.get("type") != "function_call":
                continue
            try:
                arguments = json.loads(item.get("arguments", "{}"))
                if not isinstance(arguments, dict):
                    raise ValueError
                calls.append(
                    ModelToolCall(
                        call_id=item["call_id"],
                        name=item["name"],
                        arguments=arguments,
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exception:
                raise ModelProviderError(
                    "malformed_tool_call",
                    "The AI provider produced an invalid tool call; local planning will be used.",
                ) from exception

        synthesis = None
        output_text = payload.get("output_text") or self._extract_output_text(output_items)
        if isinstance(output_text, str) and output_text.strip():
            try:
                synthesis = ModelSynthesis.model_validate_json(output_text)
            except ValidationError as exception:
                raise ModelProviderError(
                    "malformed_model_output",
                    "The AI provider returned an invalid answer; local planning will be used.",
                ) from exception
        return ModelStep(
            output_items=[item for item in output_items if isinstance(item, dict)],
            tool_calls=calls,
            synthesis=synthesis,
        )

    @staticmethod
    def _extract_output_text(output_items: list[Any]) -> str | None:
        parts: list[str] = []
        for item in output_items:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "".join(parts) or None


class GeminiInteractionsProvider:
    """Gemini Interactions API adapter with stateless, application-owned tool execution."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = client or httpx.Client(
            base_url="https://generativelanguage.googleapis.com/v1beta",
            timeout=timeout_seconds,
            headers={"x-goog-api-key": api_key},
        )
        self._call_names: dict[str, str] = {}

    @property
    def label(self) -> str:
        return f"gemini:{self.model}"

    def respond(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        tool_schemas: list[dict[str, Any]],
    ) -> ModelStep:
        tools = [
            {
                "type": "function",
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["input_schema"],
            }
            for schema in tool_schemas
        ]
        try:
            response = self.client.post(
                "/interactions",
                json={
                    "model": self.model,
                    "system_instruction": instructions,
                    "input": self._to_gemini_input(input_items),
                    "tools": tools,
                    "store": False,
                    "generation_config": {"max_output_tokens": self.max_output_tokens},
                    "response_format": {
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": SYNTHESIS_SCHEMA,
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exception:
            raise ModelProviderError(
                "model_timeout", "The AI provider timed out; local planning will be used."
            ) from exception
        except httpx.HTTPStatusError as exception:
            status_code = exception.response.status_code
            if status_code in {401, 403}:
                code = "model_authentication_failed"
            elif status_code == 429:
                code = "model_rate_limited"
            else:
                code = "model_provider_failed"
            raise ModelProviderError(
                code, "The AI provider is unavailable; local planning will be used."
            ) from exception
        except (httpx.HTTPError, ValueError) as exception:
            raise ModelProviderError(
                "model_provider_failed",
                "The AI provider returned an invalid response; local planning will be used.",
            ) from exception

        steps = payload.get("steps")
        if not isinstance(steps, list):
            raise ModelProviderError(
                "malformed_model_output",
                "The AI provider returned an invalid response; local planning will be used.",
            )
        output_items = [item for item in steps if isinstance(item, dict)]
        calls: list[ModelToolCall] = []
        for item in output_items:
            if item.get("type") != "function_call":
                continue
            try:
                arguments = item.get("arguments", {})
                if not isinstance(arguments, dict):
                    raise ValueError
                call_id = item["id"]
                name = item["name"]
                self._call_names[call_id] = name
                calls.append(ModelToolCall(call_id=call_id, name=name, arguments=arguments))
            except (KeyError, TypeError, ValueError) as exception:
                raise ModelProviderError(
                    "malformed_tool_call",
                    "The AI provider produced an invalid tool call; local planning will be used.",
                ) from exception

        synthesis = None
        output_text = payload.get("output_text") or self._extract_output_text(output_items)
        if isinstance(output_text, str) and output_text.strip():
            try:
                synthesis = ModelSynthesis.model_validate_json(output_text)
            except ValidationError as exception:
                raise ModelProviderError(
                    "malformed_model_output",
                    "The AI provider returned an invalid answer; local planning will be used.",
                ) from exception
        return ModelStep(output_items=output_items, tool_calls=calls, synthesis=synthesis)

    def _to_gemini_input(self, input_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for item in input_items:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str):
                converted.append(
                    {
                        "type": "user_input" if role == "user" else "model_output",
                        "content": [{"type": "text", "text": content}],
                    }
                )
            elif item.get("type") == "function_call_output":
                call_id = item.get("call_id")
                name = self._call_names.get(str(call_id))
                if not name:
                    raise ModelProviderError(
                        "malformed_tool_call",
                        "The AI provider produced an invalid tool call; "
                        "local planning will be used.",
                    )
                converted.append(
                    {
                        "type": "function_result",
                        "name": name,
                        "call_id": call_id,
                        "result": [{"type": "text", "text": str(item.get("output", ""))}],
                    }
                )
            else:
                converted.append(item)
        return converted

    @staticmethod
    def _extract_output_text(output_items: list[dict[str, Any]]) -> str | None:
        parts: list[str] = []
        for item in output_items:
            if item.get("type") != "model_output":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "text":
                    value = content.get("text")
                    if isinstance(value, str):
                        parts.append(value)
        return "".join(parts) or None
