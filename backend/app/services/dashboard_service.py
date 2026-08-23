from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import DashboardMetrics, DashboardSummary
from app.schemas.inspection import InspectionRead
from app.schemas.site import SiteRead


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.dashboard = DashboardRepository(session)

    def summary(self, *, now: datetime | None = None) -> DashboardSummary:
        current_time = now or datetime.now(UTC)
        month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        metrics = self.dashboard.metrics(month_start=month_start, next_month_start=next_month_start)
        return DashboardSummary(
            metrics=DashboardMetrics(**metrics),
            recent_inspections=[
                InspectionRead.model_validate(item) for item in self.dashboard.recent_inspections()
            ],
            highest_risk_sites=[
                SiteRead.model_validate(item) for item in self.dashboard.highest_risk_sites()
            ],
            anomaly_counts_by_severity=self.dashboard.anomaly_counts_by_severity(),
        )
