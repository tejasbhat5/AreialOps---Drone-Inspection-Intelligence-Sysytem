from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationError, InvalidStateError, NotFoundError
from app.models.anomaly import Anomaly
from app.models.enums import AnomalySeverity, AnomalyStatus
from app.repositories.anomaly_repository import AnomalyRepository
from app.repositories.inspection_repository import InspectionRepository
from app.repositories.site_repository import SiteRepository
from app.schemas.anomaly import AnomalyCreate, AnomalyRead, AnomalyUpdate
from app.schemas.pagination import Page, page_response
from app.services.risk_service import RiskService

ALLOWED_ANOMALY_TRANSITIONS: dict[AnomalyStatus, set[AnomalyStatus]] = {
    AnomalyStatus.OPEN: {
        AnomalyStatus.ACKNOWLEDGED,
        AnomalyStatus.RESOLVED,
        AnomalyStatus.FALSE_POSITIVE,
    },
    AnomalyStatus.ACKNOWLEDGED: {
        AnomalyStatus.OPEN,
        AnomalyStatus.RESOLVED,
        AnomalyStatus.FALSE_POSITIVE,
    },
    AnomalyStatus.RESOLVED: {AnomalyStatus.OPEN},
    AnomalyStatus.FALSE_POSITIVE: {AnomalyStatus.OPEN},
}


class AnomalyService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.anomalies = AnomalyRepository(session)
        self.inspections = InspectionRepository(session)
        self.sites = SiteRepository(session)

    def get(self, anomaly_id: UUID) -> Anomaly:
        anomaly = self.anomalies.get(anomaly_id)
        if anomaly is None:
            raise NotFoundError("Anomaly was not found.", code="anomaly_not_found")
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
    ) -> Page[AnomalyRead]:
        if site_id and self.sites.get(site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        if inspection_id and self.inspections.get(inspection_id) is None:
            raise NotFoundError("Inspection was not found.", code="inspection_not_found")
        if created_from and created_to and created_from > created_to:
            raise ApplicationError(
                "created_from must be before created_to.", code="invalid_date_range"
            )
        items, total = self.anomalies.list(
            page=page,
            page_size=page_size,
            site_id=site_id,
            inspection_id=inspection_id,
            severity=severity,
            status=status,
            unresolved_only=unresolved_only,
            created_from=created_from,
            created_to=created_to,
        )
        return page_response(
            [AnomalyRead.model_validate(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def create_for_inspection(self, inspection_id: UUID, data: AnomalyCreate) -> Anomaly:
        inspection = self.inspections.get(inspection_id)
        if inspection is None:
            raise NotFoundError("Inspection was not found.", code="inspection_not_found")
        anomaly = Anomaly(
            site_id=inspection.site_id,
            inspection_id=inspection.id,
            title=data.title,
            description=data.description,
            severity=data.severity,
            status=AnomalyStatus.OPEN,
            resolved_at=None,
        )
        self.anomalies.add(anomaly)
        RiskService(self.session).recalculate(inspection.site_id)
        self.session.commit()
        return anomaly

    def update(self, anomaly_id: UUID, data: AnomalyUpdate) -> Anomaly:
        anomaly = self.get(anomaly_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        next_status = changes.pop("status", None)
        risk_relevant_change = "severity" in changes
        if next_status and next_status != anomaly.status:
            if next_status not in ALLOWED_ANOMALY_TRANSITIONS[anomaly.status]:
                raise InvalidStateError(
                    f"Anomaly cannot move from {anomaly.status} to {next_status}.",
                    code="invalid_anomaly_transition",
                )
            anomaly.status = next_status
            anomaly.resolved_at = (
                datetime.now(UTC) if next_status == AnomalyStatus.RESOLVED else None
            )
            risk_relevant_change = True
        for field, value in changes.items():
            setattr(anomaly, field, value)
        if risk_relevant_change:
            RiskService(self.session).recalculate(anomaly.site_id)
        self.session.commit()
        return anomaly
