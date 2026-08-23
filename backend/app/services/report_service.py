from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.inspection import Inspection
from app.models.inspection_report import InspectionReport
from app.rag.retrieval_service import ReportRetrievalService
from app.schemas.reports import (
    ReportRecord,
    ReportSearchRequest,
    ReportSearchResponse,
)


class ReportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.retrieval = ReportRetrievalService(session)

    def list(self) -> list[ReportRecord]:
        reports = self.session.scalars(
            select(InspectionReport)
            .options(
                joinedload(InspectionReport.inspection).joinedload(Inspection.site),
                joinedload(InspectionReport.chunks),
            )
            .order_by(InspectionReport.created_at.desc())
        ).unique()
        return [
            ReportRecord(
                id=report.id,
                inspection_id=report.inspection_id,
                site_id=report.inspection.site_id,
                site_name=report.inspection.site.name,
                original_filename=report.original_filename,
                ingestion_status=report.ingestion_status,
                chunk_count=len(report.chunks),
                created_at=report.created_at,
            )
            for report in reports
        ]

    def search(self, data: ReportSearchRequest) -> ReportSearchResponse:
        result = self.retrieval.search(data.query, site_id=data.site_id, limit=data.limit)
        return ReportSearchResponse.model_validate(result)
