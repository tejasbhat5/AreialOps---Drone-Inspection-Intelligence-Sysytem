from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.enums import AnomalySeverity, AnomalyStatus

UNRESOLVED_STATUSES = (AnomalyStatus.OPEN, AnomalyStatus.ACKNOWLEDGED)


class AnomalyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, anomaly_id: UUID) -> Anomaly | None:
        return self.session.get(Anomaly, anomaly_id)

    def add(self, anomaly: Anomaly) -> Anomaly:
        self.session.add(anomaly)
        self.session.flush()
        return anomaly

    def list(
        self,
        *,
        page: int,
        page_size: int,
        site_id: UUID | None = None,
        inspection_id: UUID | None = None,
        severity: AnomalySeverity | None = None,
        status: AnomalyStatus | None = None,
        unresolved_only: bool = False,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[Anomaly], int]:
        statement: Select[tuple[Anomaly]] = select(Anomaly)
        if site_id:
            statement = statement.where(Anomaly.site_id == site_id)
        if inspection_id:
            statement = statement.where(Anomaly.inspection_id == inspection_id)
        if severity:
            statement = statement.where(Anomaly.severity == severity)
        if status:
            statement = statement.where(Anomaly.status == status)
        if unresolved_only:
            statement = statement.where(Anomaly.status.in_(UNRESOLVED_STATUSES))
        if created_from:
            statement = statement.where(Anomaly.created_at >= created_from)
        if created_to:
            statement = statement.where(Anomaly.created_at <= created_to)

        total = (
            self.session.scalar(
                select(func.count()).select_from(statement.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            statement.order_by(Anomaly.created_at.desc(), Anomaly.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.session.scalars(statement)), total

    def unresolved_count(self, site_id: UUID | None = None) -> int:
        statement = (
            select(func.count()).select_from(Anomaly).where(Anomaly.status.in_(UNRESOLVED_STATUSES))
        )
        if site_id:
            statement = statement.where(Anomaly.site_id == site_id)
        return self.session.scalar(statement) or 0
