from fastapi import APIRouter

from app.api.dependencies import DatabaseSession
from app.schemas.reports import ReportRecord, ReportSearchRequest, ReportSearchResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/api/reports")


@router.get("", response_model=list[ReportRecord])
def list_reports(session: DatabaseSession) -> list[ReportRecord]:
    return ReportService(session).list()


@router.post("/search", response_model=ReportSearchResponse)
def search_reports(data: ReportSearchRequest, session: DatabaseSession) -> ReportSearchResponse:
    return ReportService(session).search(data)
