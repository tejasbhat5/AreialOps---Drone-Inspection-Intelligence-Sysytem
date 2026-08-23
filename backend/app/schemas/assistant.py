from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import MessageRole
from app.schemas.agent_tools import SiteComparisonResult, SiteSearchResult
from app.schemas.base import ORMModel


class AssistantResponseType(StrEnum):
    ANSWER = "answer"
    HIGH_RISK_SITES = "high_risk_sites"
    SITE_COMPARISON = "site_comparison"
    INSPECTION_TIMELINE = "inspection_timeline"
    ANOMALY_SUMMARY = "anomaly_summary"
    RISK_EXPLANATION = "risk_explanation"
    REPORT_SUMMARY = "report_summary"
    CLARIFICATION = "clarification"
    ERROR = "error"


class ToolActivity(ORMModel):
    tool_name: str
    label: str
    status: str
    duration_ms: float = Field(ge=0)
    error_code: str | None = None


class AssistantAction(ORMModel):
    type: str
    site_id: UUID | None = None
    site_ids: list[UUID] = Field(default_factory=list, max_length=25)


class AssistantContext(ORMModel):
    current_site_id: UUID | None = None
    visible_map_site_ids: list[UUID] = Field(default_factory=list, max_length=100)


class AssistantQuery(ORMModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=2_000)
    context: AssistantContext = Field(default_factory=AssistantContext)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()


class ConversationCreate(ORMModel):
    site_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)


class AgentMessageRead(ORMModel):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    structured_payload: dict[str, Any] | None
    tool_audit: list[dict[str, Any]] | None
    created_at: datetime


class ConversationRead(ORMModel):
    id: UUID
    site_id: UUID | None
    title: str
    messages: list[AgentMessageRead]
    created_at: datetime
    updated_at: datetime


class AssistantResponse(ORMModel):
    request_id: UUID
    conversation_id: UUID
    response_type: AssistantResponseType
    answer: str
    data: SiteSearchResult | SiteComparisonResult | dict[str, Any] | None = None
    actions: list[AssistantAction] = Field(default_factory=list, max_length=20)
    tool_activity: list[ToolActivity] = Field(default_factory=list, max_length=8)
    provider: str = "deterministic-local"


class AssistantCapabilities(ORMModel):
    active_provider: str
    model: str | None = None
    model_configured: bool
    deterministic_fallback: bool = True
    max_tool_calls: int = 4
    max_model_rounds: int = 4
