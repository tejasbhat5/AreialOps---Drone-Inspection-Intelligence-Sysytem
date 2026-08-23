from __future__ import annotations

from typing import Any
from uuid import UUID

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
MAX_TOOL_CALLS = 4


class AgentOrchestrator:
    """Run a bounded local planner over the same tools a future LLM may select."""

    def __init__(
        self, registry: ToolRegistry, *, provider_label: str = "deterministic-local"
    ) -> None:
        self.registry = registry
        self.provider_label = provider_label
        self.activity: list[ToolActivity] = []
        self.calls = 0

    def _call(self, name: str, arguments: dict[str, Any], request_id: UUID) -> ToolExecutionResult:
        if self.calls >= MAX_TOOL_CALLS:
            return ToolExecutionResult(
                tool_name=name,
                ok=False,
                error={"code": "tool_call_limit", "message": "The tool-call limit was reached."},
                duration_ms=0,
            )
        self.calls += 1
        result = self.registry.execute(name, arguments, request_id=request_id)
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

    def run(
        self,
        *,
        message: str,
        context: AssistantContext,
        request_id: UUID,
        conversation_id: UUID,
    ) -> AssistantResponse:
        normalized = " ".join(message.lower().split())
        if "compare" in normalized:
            return self._compare_top(request_id, conversation_id)
        if any(
            term in normalized
            for term in (
                "highest risk",
                "highest-risk",
                "high-risk sites",
                "high risk sites",
                "critical sites",
                "sites are critical",
            )
        ):
            return self._high_risk(request_id, conversation_id)
        if context.current_site_id:
            return self._for_site(context.current_site_id, normalized, request_id, conversation_id)

        if any(term in normalized for term in ("report", "reported", "document")):
            return self._report_search(normalized, None, request_id, conversation_id)

        discovery = self._call("search_sites", {"limit": 25}, request_id)
        if discovery.ok and discovery.data:
            matches = [
                site for site in discovery.data["sites"] if str(site["name"]).lower() in normalized
            ]
            if len(matches) == 1:
                return self._for_site(
                    UUID(matches[0]["id"]), normalized, request_id, conversation_id
                )
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.CLARIFICATION,
            "I can inspect a named site, explain its risk, list unresolved findings, "
            "show inspection history, or compare the highest-risk sites. Please choose "
            "one of those operations.",
            data={
                "suggestions": [
                    "Show the highest-risk sites",
                    "Compare the two highest-risk sites",
                    "Why is Solar Farm Alpha high risk?",
                    "Show unresolved findings for Solar Farm Alpha",
                    "What was reported during the previous inspection at Solar Farm Alpha?",
                ]
            },
        )

    def _for_site(
        self,
        site_id: UUID,
        message: str,
        request_id: UUID,
        conversation_id: UUID,
    ) -> AssistantResponse:
        if "generate" in message and "report" in message:
            result = self._call("generate_site_report", {"site_id": str(site_id)}, request_id)
            if not result.ok:
                return self._tool_error(result, request_id, conversation_id)
            return self._response(
                request_id,
                conversation_id,
                AssistantResponseType.REPORT_SUMMARY,
                "Generated a grounded operational report from site, risk, anomaly, "
                "and report data.",
                data=result.data,
                actions=[AssistantAction(type="OPEN_SITE", site_id=site_id)],
            )
        if any(term in message for term in ("report", "reported", "document")):
            return self._report_search(message, site_id, request_id, conversation_id)
        if any(term in message for term in ("anomal", "finding", "issue", "defect")):
            return self._site_records(
                "get_site_anomalies",
                AssistantResponseType.ANOMALY_SUMMARY,
                site_id,
                request_id,
                conversation_id,
            )
        if any(term in message for term in ("inspection", "timeline", "history")):
            return self._site_records(
                "get_inspections",
                AssistantResponseType.INSPECTION_TIMELINE,
                site_id,
                request_id,
                conversation_id,
            )
        if any(term in message for term in ("risk", "score", "why")):
            return self._site_risk(site_id, request_id, conversation_id)
        result = self._call("get_site_details", {"site_id": str(site_id)}, request_id)
        if not result.ok:
            return self._tool_error(result, request_id, conversation_id)
        site = result.data or {}
        asset_type = str(site.get("site_type", "")).lower().replace("_", " ")
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.ANSWER,
            f"{site.get('name')} is a {asset_type} in {site.get('location')} with "
            f"risk {site.get('risk_score')}/100 ({site.get('risk_level')}).",
            data=site,
            actions=[AssistantAction(type="OPEN_SITE", site_id=site_id)],
        )

    def _report_search(
        self,
        query: str,
        site_id: UUID | None,
        request_id: UUID,
        conversation_id: UUID,
    ) -> AssistantResponse:
        arguments: dict[str, Any] = {"query": query, "limit": 5}
        if site_id:
            arguments["site_id"] = str(site_id)
        result = self._call("search_reports", arguments, request_id)
        if not result.ok:
            return self._tool_error(result, request_id, conversation_id)
        data = result.data or {}
        citations = data.get("citations", [])
        if not citations:
            answer = "No indexed report passage matched that question."
        else:
            answer = (
                f"Found {len(citations)} grounded report passage"
                f"{'s' if len(citations) != 1 else ''}. The strongest source says: "
                f"{citations[0]['excerpt']}"
            )
        action_site = UUID(citations[0]["site_id"]) if citations else site_id
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.REPORT_SUMMARY,
            answer,
            data=data,
            actions=[AssistantAction(type="OPEN_SITE", site_id=action_site)] if action_site else [],
        )

    def _high_risk(self, request_id: UUID, conversation_id: UUID) -> AssistantResponse:
        result = self._call("find_high_risk_sites", {"limit": 5}, request_id)
        if not result.ok:
            return self._tool_error(result, request_id, conversation_id)
        sites = result.data["sites"] if result.data else []
        count = len(sites)
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.HIGH_RISK_SITES,
            f"Found {count} high or critical-risk site{'s' if count != 1 else ''}, "
            "ordered by the authoritative deterministic score.",
            data=result.data,
            actions=[
                AssistantAction(type="HIGHLIGHT_MAP", site_ids=[UUID(site["id"]) for site in sites])
            ],
        )

    def _compare_top(self, request_id: UUID, conversation_id: UUID) -> AssistantResponse:
        candidates = self._call("find_high_risk_sites", {"limit": 2}, request_id)
        if not candidates.ok:
            return self._tool_error(candidates, request_id, conversation_id)
        sites = candidates.data["sites"] if candidates.data else []
        if len(sites) < 2:
            return self._response(
                request_id,
                conversation_id,
                AssistantResponseType.CLARIFICATION,
                "At least two high-risk sites are required for this comparison.",
                data=candidates.data,
            )
        comparison = self._call(
            "compare_sites",
            {"site_a": sites[0]["id"], "site_b": sites[1]["id"]},
            request_id,
        )
        if not comparison.ok:
            return self._tool_error(comparison, request_id, conversation_id)
        data = comparison.data or {}
        recommended_id = data.get("recommended_site_id")
        recommended = next(
            (site for site in data.get("sites", []) if site["id"] == recommended_id), None
        )
        answer = (
            f"{recommended['name']} should be reviewed first. " + " ".join(data.get("reasons", []))
            if recommended
            else "The sites were compared using current operational facts."
        )
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.SITE_COMPARISON,
            answer,
            data=data,
            actions=[AssistantAction(type="OPEN_SITE", site_id=UUID(recommended_id))]
            if recommended_id
            else [],
        )

    def _site_risk(
        self, site_id: UUID, request_id: UUID, conversation_id: UUID
    ) -> AssistantResponse:
        result = self._call("calculate_site_risk", {"site_id": str(site_id)}, request_id)
        if not result.ok:
            return self._tool_error(result, request_id, conversation_id)
        data = result.data or {}
        factors = data.get("factors", {})
        answer = (
            f"The deterministic risk is {data.get('score')}/100 ({data.get('level')}). "
            f"It consists of {factors.get('severity_points', 0)} severity points, "
            f"{factors.get('critical_bonus', 0)} critical bonus, "
            f"{factors.get('volume_points', 0)} volume points, and "
            f"{factors.get('recency_points', 0)} recency points."
        )
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.RISK_EXPLANATION,
            answer,
            data=data,
            actions=[AssistantAction(type="OPEN_SITE", site_id=site_id)],
        )

    def _site_records(
        self,
        tool_name: str,
        response_type: AssistantResponseType,
        site_id: UUID,
        request_id: UUID,
        conversation_id: UUID,
    ) -> AssistantResponse:
        result = self._call(tool_name, {"site_id": str(site_id), "limit": 20}, request_id)
        if not result.ok:
            return self._tool_error(result, request_id, conversation_id)
        data = result.data or {}
        total = data.get("total_unresolved", data.get("total", 0))
        noun = "unresolved finding" if tool_name == "get_site_anomalies" else "inspection"
        return self._response(
            request_id,
            conversation_id,
            response_type,
            f"Found {total} {noun}{'s' if total != 1 else ''} for this site.",
            data=data,
            actions=[AssistantAction(type="OPEN_SITE", site_id=site_id)],
        )

    def _tool_error(
        self, result: ToolExecutionResult, request_id: UUID, conversation_id: UUID
    ) -> AssistantResponse:
        error = result.error
        return self._response(
            request_id,
            conversation_id,
            AssistantResponseType.ERROR,
            error.message if error else "The operational tool failed safely.",
            data={"error_code": error.code if error else "tool_execution_failed"},
        )

    def _response(
        self,
        request_id: UUID,
        conversation_id: UUID,
        response_type: AssistantResponseType,
        answer: str,
        *,
        data: Any = None,
        actions: list[AssistantAction] | None = None,
    ) -> AssistantResponse:
        response = AssistantResponse(
            request_id=request_id,
            conversation_id=conversation_id,
            response_type=response_type,
            answer=answer,
            data=data,
            actions=actions or [],
            tool_activity=self.activity,
            provider=self.provider_label,
        )
        logger.info(
            "agent_request_completed",
            extra={
                "agent_request_id": str(request_id),
                "conversation_id": str(conversation_id),
                "response_type": response_type.value,
                "tool_calls": self.calls,
                "provider": response.provider,
            },
        )
        return response
