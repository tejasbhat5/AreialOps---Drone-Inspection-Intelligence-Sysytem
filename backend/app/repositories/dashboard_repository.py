from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.anomaly import Anomaly
from app.models.enums import (
    AnomalySeverity,
    AnomalyStatus,
    RiskLevel,
    SiteStatus,
)
from app.models.inspection import Inspection
from app.models.site import Site


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def metrics(
        self, *, month_start: datetime, next_month_start: datetime
    ) -> dict[str, float | int]:
        total_sites = self.session.scalar(select(func.count()).select_from(Site)) or 0
        active_sites = (
            self.session.scalar(
                select(func.count()).select_from(Site).where(Site.status == SiteStatus.ACTIVE)
            )
            or 0
        )
        critical_sites = (
            self.session.scalar(
                select(func.count())
                .select_from(Site)
                .where(Site.current_risk_level == RiskLevel.CRITICAL)
            )
            or 0
        )
        inspections_this_month = (
            self.session.scalar(
                select(func.count())
                .select_from(Inspection)
                .where(
                    Inspection.inspected_at >= month_start,
                    Inspection.inspected_at < next_month_start,
                )
            )
            or 0
        )
        unresolved_anomalies = (
            self.session.scalar(
                select(func.count())
                .select_from(Anomaly)
                .where(Anomaly.status.in_((AnomalyStatus.OPEN, AnomalyStatus.ACKNOWLEDGED)))
            )
            or 0
        )
        average_risk = self.session.scalar(select(func.avg(Site.current_risk_score))) or 0
        return {
            "total_sites": total_sites,
            "active_sites": active_sites,
            "critical_sites": critical_sites,
            "inspections_this_month": inspections_this_month,
            "unresolved_anomalies": unresolved_anomalies,
            "average_risk_score": round(float(average_risk), 1),
        }

    def recent_inspections(self, limit: int = 5) -> list[Inspection]:
        statement = (
            select(Inspection)
            .options(selectinload(Inspection.anomalies))
            .order_by(Inspection.inspected_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def highest_risk_sites(self, limit: int = 5) -> list[Site]:
        statement = select(Site).order_by(Site.current_risk_score.desc(), Site.name).limit(limit)
        return list(self.session.scalars(statement))

    def anomaly_counts_by_severity(self) -> dict[str, int]:
        rows = self.session.execute(
            select(Anomaly.severity, func.count()).group_by(Anomaly.severity)
        ).all()
        counts = {severity.value: 0 for severity in AnomalySeverity}
        counts.update({severity.value: count for severity, count in rows})
        return counts
