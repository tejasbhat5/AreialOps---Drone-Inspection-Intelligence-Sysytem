from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.enums import (
    AnomalySeverity,
    AnomalyStatus,
    InspectionStatus,
    RiskLevel,
    SiteStatus,
    SiteType,
)
from app.rag.schemas import ReportCitation
from app.schemas.base import ORMModel


class EmptyToolInput(ORMModel):
    pass


class SiteIdInput(ORMModel):
    site_id: UUID


class SearchSitesInput(ORMModel):
    query: str | None = Field(default=None, min_length=1, max_length=150)
    site_type: SiteType | None = None
    status: SiteStatus | None = None
    risk_levels: list[RiskLevel] | None = Field(default=None, max_length=4)
    limit: int = Field(default=10, ge=1, le=25)


class SiteListInput(ORMModel):
    limit: int = Field(default=5, ge=1, le=20)


class SiteRecordsInput(SiteIdInput):
    limit: int = Field(default=10, ge=1, le=50)


class CompareSitesInput(ORMModel):
    site_a: UUID
    site_b: UUID


class SearchReportsInput(ORMModel):
    query: str = Field(min_length=2, max_length=500)
    site_id: UUID | None = None
    limit: int = Field(default=5, ge=1, le=10)


class InspectionSummary(ORMModel):
    id: UUID
    site_id: UUID
    inspected_at: datetime
    status: InspectionStatus
    notes: str | None
    anomaly_count: int = Field(ge=0)


class AnomalySummary(ORMModel):
    id: UUID
    site_id: UUID
    inspection_id: UUID
    title: str
    severity: AnomalySeverity
    status: AnomalyStatus
    description: str


class SiteOperationalView(ORMModel):
    id: UUID
    name: str
    site_type: SiteType
    status: SiteStatus
    location: str
    latitude: float
    longitude: float
    risk_score: int
    risk_level: RiskLevel
    unresolved_anomalies: int
    latest_inspection_at: datetime | None


class SiteSearchResult(ORMModel):
    sites: list[SiteOperationalView]
    total: int = Field(ge=0)


class InspectionResult(ORMModel):
    inspection: InspectionSummary | None


class InspectionsResult(ORMModel):
    inspections: list[InspectionSummary]
    total: int = Field(ge=0)


class AnomaliesResult(ORMModel):
    anomalies: list[AnomalySummary]
    total_unresolved: int = Field(ge=0)


class RiskToolResult(ORMModel):
    site_id: UUID
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    formula_version: str
    factors: dict[str, Any]


class SiteComparisonResult(ORMModel):
    sites: list[SiteOperationalView] = Field(min_length=2, max_length=2)
    recommended_site_id: UUID
    reasons: list[str] = Field(min_length=1, max_length=5)


class ReportSearchToolResult(ORMModel):
    query: str
    citations: list[ReportCitation]
    total: int = Field(ge=0)


class GeneratedSiteReport(ORMModel):
    site: SiteOperationalView
    inspections_reviewed: int = Field(ge=0)
    unresolved_anomalies: list[AnomalySummary]
    risk: RiskToolResult
    report_citations: list[ReportCitation]


class ToolFailure(ORMModel):
    code: str
    message: str


class ToolExecutionResult(ORMModel):
    tool_name: str
    ok: bool
    data: dict[str, Any] | None = None
    error: ToolFailure | None = None
    duration_ms: float = Field(ge=0)
