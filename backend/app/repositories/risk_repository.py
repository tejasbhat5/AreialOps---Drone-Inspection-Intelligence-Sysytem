from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyStatus, InspectionStatus
from app.models.inspection import Inspection
from app.models.risk_assessment import RiskAssessment

UNRESOLVED_STATUSES = (AnomalyStatus.OPEN, AnomalyStatus.ACKNOWLEDGED)


class RiskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def unresolved_anomalies(self, site_id: UUID) -> list[Anomaly]:
        return list(
            self.session.scalars(
                select(Anomaly).where(
                    Anomaly.site_id == site_id,
                    Anomaly.status.in_(UNRESOLVED_STATUSES),
                )
            )
        )

    def latest_completed_inspection_at(self, site_id: UUID):
        return self.session.scalar(
            select(func.max(Inspection.inspected_at)).where(
                Inspection.site_id == site_id,
                Inspection.status == InspectionStatus.COMPLETED,
            )
        )

    def add(self, assessment: RiskAssessment) -> RiskAssessment:
        self.session.add(assessment)
        self.session.flush()
        return assessment

    def latest(self, site_id: UUID) -> RiskAssessment | None:
        return self.session.scalar(
            select(RiskAssessment)
            .where(RiskAssessment.site_id == site_id)
            .order_by(RiskAssessment.calculated_at.desc(), RiskAssessment.id.desc())
            .limit(1)
        )

    def history(self, site_id: UUID, *, limit: int = 20) -> list[RiskAssessment]:
        return list(
            self.session.scalars(
                select(RiskAssessment)
                .where(RiskAssessment.site_id == site_id)
                .order_by(RiskAssessment.calculated_at.desc(), RiskAssessment.id.desc())
                .limit(limit)
            )
        )
