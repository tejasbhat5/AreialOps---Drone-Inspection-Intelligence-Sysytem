from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.models.inspection import Inspection
from app.models.inspection_report import InspectionReport
from app.models.report_chunk import ReportChunk


class ReportVectorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace(self, report_id: UUID, chunks: list[ReportChunk]) -> None:
        self.session.execute(delete(ReportChunk).where(ReportChunk.report_id == report_id))
        self.session.add_all(chunks)
        self.session.flush()

    def searchable(self, *, site_id: UUID | None = None) -> list[ReportChunk]:
        statement = (
            select(ReportChunk)
            .join(ReportChunk.report)
            .join(InspectionReport.inspection)
            .options(
                joinedload(ReportChunk.report)
                .joinedload(InspectionReport.inspection)
                .joinedload(Inspection.site)
            )
        )
        if site_id:
            statement = statement.where(InspectionReport.inspection.has(site_id=site_id))
        return list(self.session.scalars(statement.order_by(ReportChunk.created_at.desc())))
