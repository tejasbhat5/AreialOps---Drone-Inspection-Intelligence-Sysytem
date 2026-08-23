from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ValidationError

from app.core.exceptions import ApplicationError
from app.core.logging import get_logger
from app.schemas.agent_tools import ToolExecutionResult, ToolFailure

logger = get_logger(__name__)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    label: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[[BaseModel], BaseModel]


class ToolRegistry:
    def __init__(self, definitions: list[ToolDefinition]) -> None:
        self._definitions = {definition.name: definition for definition in definitions}
        if len(self._definitions) != len(definitions):
            raise ValueError("Tool names must be unique.")

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._definitions)

    def label_for(self, name: str) -> str:
        definition = self._definitions.get(name)
        return definition.label if definition else name.replace("_", " ").title()

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "input_schema": definition.input_model.model_json_schema(),
                "output_schema": definition.output_model.model_json_schema(),
            }
            for definition in self._definitions.values()
        ]

    def execute(
        self, name: str, arguments: dict[str, Any], *, request_id: UUID
    ) -> ToolExecutionResult:
        started = time.perf_counter()
        definition = self._definitions.get(name)
        if definition is None:
            return self._failure(
                name,
                started,
                code="tool_not_allowed",
                message="The requested tool is not registered.",
                request_id=request_id,
            )
        try:
            validated_input = definition.input_model.model_validate(arguments)
            raw_output = definition.handler(validated_input)
            validated_output = definition.output_model.model_validate(raw_output)
        except ValidationError:
            return self._failure(
                name,
                started,
                code="invalid_tool_arguments",
                message="Tool input or output validation failed.",
                request_id=request_id,
            )
        except ApplicationError as exception:
            return self._failure(
                name,
                started,
                code=exception.code,
                message=exception.message,
                request_id=request_id,
            )
        except Exception:
            logger.exception(
                "agent_tool_failed",
                extra={"agent_request_id": str(request_id), "tool_name": name},
            )
            return self._failure(
                name,
                started,
                code="tool_execution_failed",
                message="The requested operational data could not be retrieved.",
                request_id=request_id,
            )
        duration = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "agent_tool_completed",
            extra={
                "agent_request_id": str(request_id),
                "tool_name": name,
                "duration_ms": duration,
            },
        )
        return ToolExecutionResult(
            tool_name=name,
            ok=True,
            data=validated_output.model_dump(mode="json"),
            duration_ms=duration,
        )

    def _failure(
        self,
        name: str,
        started: float,
        *,
        code: str,
        message: str,
        request_id: UUID,
    ) -> ToolExecutionResult:
        duration = round((time.perf_counter() - started) * 1000, 2)
        logger.warning(
            "agent_tool_rejected",
            extra={
                "agent_request_id": str(request_id),
                "tool_name": name,
                "error_code": code,
                "duration_ms": duration,
            },
        )
        return ToolExecutionResult(
            tool_name=name,
            ok=False,
            error=ToolFailure(code=code, message=message),
            duration_ms=duration,
        )
