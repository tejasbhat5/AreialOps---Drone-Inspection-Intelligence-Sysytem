from fastapi import APIRouter

from app.api.dependencies import DatabaseSession
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard")


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(session: DatabaseSession) -> DashboardSummary:
    return DashboardService(session).summary()
