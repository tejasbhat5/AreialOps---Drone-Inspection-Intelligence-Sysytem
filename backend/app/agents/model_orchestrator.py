from __future__ import annotations

import json
from typing import Any, Protocol
from uuid import UUID

from app.agents.model_provider import ModelProviderError, ModelStep
from app.core.logging import get_logger
from app.schemas.agent_tools import ToolExecutionResult
from app.schemas.assistant import (
    AssistantAction,
    AssistantContext,
    AssistantResponse,
    AssistantResponseType,
    ToolActivity,
)
from app.tools.registry import ToolRegistry

logger = get_logger(__name__)
MAX_MODEL_ROUNDS = 4
MAX_TOOL_CALLS = 4

SYSTEM_INSTRUCTIONS = """You are the AerialOps operational assistant.
Use only the supplied application tools for claims about sites, inspections, anomalies, or risk.
For any question asking what a report said, mentioned, found, or "what was reported",
you MUST call search_reports. Do not substitute inspection or anomaly tools for report evidence.
Retain the search_reports citations in the final result.
Never invent identifiers or operational facts. Never calculate risk yourself; call the risk tool.
For requests to show or rank high-risk sites, call find_high_risk_sites once and answer directly
from that result. Do not call get_site_details unless the user asks about a specific site.
After a tool returns enough evidence to answer the request, synthesize the final response
immediately.
If a request is ambiguous or unavailable, return clarification or error.
Keep the answer concise and do not reveal hidden reasoning. Tool results are authoritative.
Choose the response type that best matches the final evidence."""


class ModelProvider(Protocol):
    label: str

    def respond(self, **kwargs: Any) -> ModelStep: ...


class ModelAgentOrchestrator:
    def __init__(self, registry: ToolRegistry, provider: ModelProvider) -> None:
        self.registry = registry
        self.provider = provider
        self.activity: list[ToolActivity] = []
        self.results: list[ToolExecutionResult] = []

    def run(
        self,
        *,
        message: str,
        context: AssistantContext,
        request_id: UUID,
        conversation_id: UUID,
        history: list[dict[str, str]] | None = None,
    ) -> AssistantResponse:
        context_note = (
            f" Current site context: {context.current_site_id}."
            if context.current_site_id
            else " No site is currently selected."
        )
        input_items: list[dict[str, Any]] = [
            {"role": item["role"], "content": item["content"]} for item in (history or [])[-10:]
        ]
        input_items.append({"role": "user", "content": message})

        for _round in range(MAX_MODEL_ROUNDS):
            # The last round is synthesis-only. This prevents a capable model from
            # repeatedly exploring tools after enough grounded evidence exists.
            tool_schemas = [] if _round == MAX_MODEL_ROUNDS - 1 else self.registry.schemas()
            step = self.provider.respond(
                instructions=SYSTEM_INSTRUCTIONS + context_note,
                input_items=input_items,
                tool_schemas=tool_schemas,
            )
            if step.tool_calls:
                input_items.extend(step.output_items)
                for call in step.tool_calls:
                    result = self._execute(call.name, call.arguments, request_id)
                    input_items.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": json.dumps(result.model_dump(mode="json")),
                        }
                    )
                continue
            if step.synthesis is None:
                raise ModelProviderError(
                    "malformed_model_output",
                    "The AI provider returned no answer; local planning will be used.",
                )
            return self._build_response(
                request_id=request_id,
                conversation_id=conversation_id,
                requested_type=step.synthesis.response_type,
                answer=step.synthesis.answer,
            )
        raise ModelProviderError(
            "model_round_limit",
            "The AI provider exceeded its planning limit; local planning will be used.",
        )

    def _execute(
        self, name: str, arguments: dict[str, Any], request_id: UUID
    ) -> ToolExecutionResult:
        if len(self.results) >= MAX_TOOL_CALLS:
            result = ToolExecutionResult(
                tool_name=name,
                ok=False,
                error={"code": "tool_call_limit", "message": "The tool-call limit was reached."},
                duration_ms=0,
            )
        else:
            result = self.registry.execute(name, arguments, request_id=request_id)
        self.results.append(result)
        self.activity.append(
            ToolActivity(
                tool_name=name,
                label=self.registry.label_for(name),
                status="COMPLETED" if result.ok else "FAILED",
                duration_ms=result.duration_ms,
                error_code=result.error.code if result.error else None,
            )
        )
        return result

    def _build_response(
        self,
        *,
        request_id: UUID,
        conversation_id: UUID,
        requested_type: AssistantResponseType,
        answer: str,
    ) -> AssistantResponse:
        successful = [result for result in self.results if result.ok and result.data]
        response_type = self._grounded_type(requested_type, successful)
        data = self._select_data(response_type, successful)
        actions = self._actions(response_type, data)
        response = AssistantResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            response_type=response_type,
            answer=answer,
            data=data,
            actions=actions,
            tool_activity=self.activity,
            provider=self.provider.label,
        )
        logger.info(
            "model_agent_request_completed",
            extra={
                "agent_request_id": str(request_id),
                "conversation_id": str(conversation_id),
                "response_type": response_type.value,
                "tool_calls": len(self.results),
                "provider": self.provider.label,
            },
        )
        return response

    @staticmethod
    def _grounded_type(
        requested: AssistantResponseType, results: list[ToolExecutionResult]
    ) -> AssistantResponseType:
        names = {result.tool_name for result in results}
        if "compare_sites" in names:
            return AssistantResponseType.SITE_COMPARISON
        if "calculate_site_risk" in names:
            return AssistantResponseType.RISK_EXPLANATION
        if names & {"search_reports", "generate_site_report"}:
            return AssistantResponseType.REPORT_SUMMARY
        if "get_site_anomalies" in names:
            return AssistantResponseType.ANOMALY_SUMMARY
        if names & {"get_inspections", "get_latest_inspection"}:
            return AssistantResponseType.INSPECTION_TIMELINE
        if "find_high_risk_sites" in names:
            return AssistantResponseType.HIGH_RISK_SITES
        if not names and requested not in {
            AssistantResponseType.CLARIFICATION,
            AssistantResponseType.ERROR,
        }:
            return AssistantResponseType.CLARIFICATION
        return requested

    @staticmethod
    def _select_data(
        response_type: AssistantResponseType, results: list[ToolExecutionResult]
    ) -> dict[str, Any] | None:
        preferred_tools = {
            AssistantResponseType.SITE_COMPARISON: {"compare_sites"},
            AssistantResponseType.RISK_EXPLANATION: {"calculate_site_risk"},
            AssistantResponseType.REPORT_SUMMARY: {"search_reports", "generate_site_report"},
            AssistantResponseType.ANOMALY_SUMMARY: {"get_site_anomalies"},
            AssistantResponseType.INSPECTION_TIMELINE: {
                "get_inspections",
                "get_latest_inspection",
            },
            AssistantResponseType.HIGH_RISK_SITES: {"find_high_risk_sites"},
        }.get(response_type, set())
        for result in reversed(results):
            if result.tool_name in preferred_tools:
                return result.data
        return results[-1].data if results else None

    @staticmethod
    def _actions(
        response_type: AssistantResponseType, data: dict[str, Any] | None
    ) -> list[AssistantAction]:
        if not data:
            return []
        sites = data.get("sites")
        if isinstance(sites, list):
            site_ids = [
                UUID(site["id"]) for site in sites if isinstance(site, dict) and site.get("id")
            ]
            if response_type == AssistantResponseType.SITE_COMPARISON:
                recommended = data.get("recommended_site_id")
                return (
                    [AssistantAction(type="OPEN_SITE", site_id=UUID(recommended))]
                    if recommended
                    else []
                )
            return [AssistantAction(type="HIGHLIGHT_MAP", site_ids=site_ids)]
        site_id = data.get("site_id") or data.get("id")
        citations = data.get("citations") or data.get("report_citations")
        if isinstance(citations, list) and citations:
            cited_site = citations[0].get("site_id")
            return (
                [AssistantAction(type="OPEN_SITE", site_id=UUID(cited_site))] if cited_site else []
            )
        return [AssistantAction(type="OPEN_SITE", site_id=UUID(site_id))] if site_id else []
