from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.rag.retrieval_service import ReportRetrievalService
from app.schemas.agent_tools import (
    AnomaliesResult,
    AnomalySummary,
    CompareSitesInput,
    GeneratedSiteReport,
    InspectionResult,
    InspectionsResult,
    InspectionSummary,
    ReportSearchToolResult,
    RiskToolResult,
    SearchReportsInput,
    SearchSitesInput,
    SiteComparisonResult,
    SiteIdInput,
    SiteListInput,
    SiteOperationalView,
    SiteRecordsInput,
    SiteSearchResult,
)
from app.services.anomaly_service import AnomalyService
from app.services.inspection_service import InspectionService
from app.services.risk_service import FORMULA_VERSION, RiskService
from app.services.site_service import SiteService
from app.tools.registry import ToolDefinition, ToolRegistry


class OperationalTools:
    def __init__(self, session: Session) -> None:
        self.sites = SiteService(session)
        self.inspections = InspectionService(session)
        self.anomalies = AnomalyService(session)
        self.risks = RiskService(session)
        self.reports = ReportRetrievalService(session)

    def site_view(self, site_id) -> SiteOperationalView:
        site = self.sites.get_detail(site_id)
        latest = self.inspections.list(page=1, page_size=1, site_id=site_id)
        return SiteOperationalView(
            id=site.id,
            name=site.name,
            site_type=site.site_type,
            status=site.status,
            location=site.location,
            latitude=float(site.latitude),
            longitude=float(site.longitude),
            risk_score=site.current_risk_score,
            risk_level=site.current_risk_level,
            unresolved_anomalies=site.unresolved_anomaly_count,
            latest_inspection_at=latest.items[0].inspected_at if latest.items else None,
        )

    def get_site_details(self, raw) -> SiteOperationalView:
        data = cast(SiteIdInput, raw)
        return self.site_view(data.site_id)

    def search_sites(self, raw) -> SiteSearchResult:
        data = cast(SearchSitesInput, raw)
        result = self.sites.list(
            page=1,
            page_size=data.limit,
            query=data.query,
            site_type=data.site_type,
            status=data.status,
            risk_levels=data.risk_levels,
            sort="risk_desc" if data.risk_levels else "name",
        )
        return SiteSearchResult(
            sites=[self.site_view(site.id) for site in result.items], total=result.total
        )

    @staticmethod
    def inspection_summary(inspection) -> InspectionSummary:
        return InspectionSummary(
            id=inspection.id,
            site_id=inspection.site_id,
            inspected_at=inspection.inspected_at,
            status=inspection.status,
            notes=inspection.notes,
            anomaly_count=len(inspection.anomalies),
        )

    def get_latest_inspection(self, raw) -> InspectionResult:
        data = cast(SiteIdInput, raw)
        result = self.inspections.list(page=1, page_size=1, site_id=data.site_id)
        return InspectionResult(
            inspection=self.inspection_summary(result.items[0]) if result.items else None
        )

    def get_inspections(self, raw) -> InspectionsResult:
        data = cast(SiteRecordsInput, raw)
        result = self.inspections.list(page=1, page_size=data.limit, site_id=data.site_id)
        return InspectionsResult(
            inspections=[self.inspection_summary(item) for item in result.items],
            total=result.total,
        )

    def get_site_anomalies(self, raw) -> AnomaliesResult:
        data = cast(SiteRecordsInput, raw)
        result = self.anomalies.list(
            page=1,
            page_size=data.limit,
            site_id=data.site_id,
            unresolved_only=True,
        )
        return AnomaliesResult(
            anomalies=[
                AnomalySummary(
                    id=item.id,
                    site_id=item.site_id,
                    inspection_id=item.inspection_id,
                    title=item.title,
                    severity=item.severity,
                    status=item.status,
                    description=item.description,
                )
                for item in result.items
            ],
            total_unresolved=result.total,
        )

    def find_high_risk_sites(self, raw) -> SiteSearchResult:
        data = cast(SiteListInput, raw)
        result = self.sites.list(
            page=1,
            page_size=data.limit,
            risk_levels=[RiskLevel.HIGH, RiskLevel.CRITICAL],
            sort="risk_desc",
        )
        return SiteSearchResult(
            sites=[self.site_view(site.id) for site in result.items], total=result.total
        )

    def compare_sites(self, raw) -> SiteComparisonResult:
        data = cast(CompareSitesInput, raw)
        first = self.site_view(data.site_a)
        second = self.site_view(data.site_b)
        ordered = sorted(
            [first, second],
            key=lambda site: (site.risk_score, site.unresolved_anomalies),
            reverse=True,
        )
        recommended = ordered[0]
        reasons = [
            f"{recommended.name} has the higher authoritative risk score "
            f"({recommended.risk_score})."
        ]
        if first.unresolved_anomalies != second.unresolved_anomalies:
            reasons.append(
                f"It has {recommended.unresolved_anomalies} unresolved findings requiring review."
            )
        return SiteComparisonResult(
            sites=[first, second], recommended_site_id=recommended.id, reasons=reasons
        )

    def calculate_site_risk(self, raw) -> RiskToolResult:
        data = cast(SiteIdInput, raw)
        calculation = self.risks.calculate(data.site_id)
        return RiskToolResult(
            site_id=data.site_id,
            score=calculation.score,
            level=calculation.level,
            formula_version=FORMULA_VERSION,
            factors=calculation.factors,
        )

    def search_reports(self, raw) -> ReportSearchToolResult:
        data = cast(SearchReportsInput, raw)
        result = self.reports.search(data.query, site_id=data.site_id, limit=data.limit)
        return ReportSearchToolResult.model_validate(result)

    def generate_site_report(self, raw) -> GeneratedSiteReport:
        data = cast(SiteIdInput, raw)
        site = self.site_view(data.site_id)
        inspections = self.inspections.list(page=1, page_size=20, site_id=data.site_id)
        anomalies = self.get_site_anomalies(SiteRecordsInput(site_id=data.site_id, limit=20))
        risk = self.calculate_site_risk(SiteIdInput(site_id=data.site_id))
        citations = self.reports.search(
            "inspection findings condition recommendations follow-up",
            site_id=data.site_id,
            limit=5,
        )
        return GeneratedSiteReport(
            site=site,
            inspections_reviewed=inspections.total,
            unresolved_anomalies=anomalies.anomalies,
            risk=risk,
            report_citations=citations.citations,
        )


def build_operational_tool_registry(session: Session) -> ToolRegistry:
    tools = OperationalTools(session)
    return ToolRegistry(
        [
            ToolDefinition(
                "get_site_details",
                "Loading site details",
                "Get one site and its operational snapshot.",
                SiteIdInput,
                SiteOperationalView,
                tools.get_site_details,
            ),
            ToolDefinition(
                "search_sites",
                "Searching sites",
                "Search and filter registered sites.",
                SearchSitesInput,
                SiteSearchResult,
                tools.search_sites,
            ),
            ToolDefinition(
                "get_latest_inspection",
                "Loading latest inspection",
                "Get the latest inspection for a site.",
                SiteIdInput,
                InspectionResult,
                tools.get_latest_inspection,
            ),
            ToolDefinition(
                "get_inspections",
                "Loading inspection timeline",
                "Get bounded inspection history for a site.",
                SiteRecordsInput,
                InspectionsResult,
                tools.get_inspections,
            ),
            ToolDefinition(
                "get_site_anomalies",
                "Reviewing unresolved findings",
                "Get bounded unresolved anomalies for a site.",
                SiteRecordsInput,
                AnomaliesResult,
                tools.get_site_anomalies,
            ),
            ToolDefinition(
                "find_high_risk_sites",
                "Finding high-risk sites",
                "List high and critical sites by score.",
                SiteListInput,
                SiteSearchResult,
                tools.find_high_risk_sites,
            ),
            ToolDefinition(
                "compare_sites",
                "Comparing site conditions",
                "Compare two sites using operational facts.",
                CompareSitesInput,
                SiteComparisonResult,
                tools.compare_sites,
            ),
            ToolDefinition(
                "calculate_site_risk",
                "Calculating deterministic risk",
                "Calculate risk without allowing an LLM to alter the formula.",
                SiteIdInput,
                RiskToolResult,
                tools.calculate_site_risk,
            ),
            ToolDefinition(
                "search_reports",
                "Searching inspection reports",
                "Retrieve source-citing report passages using local semantic search.",
                SearchReportsInput,
                ReportSearchToolResult,
                tools.search_reports,
            ),
            ToolDefinition(
                "generate_site_report",
                "Generating grounded site report",
                "Compile site, inspection, risk, anomaly, and report evidence.",
                SiteIdInput,
                GeneratedSiteReport,
                tools.generate_site_report,
            ),
        ]
    )
