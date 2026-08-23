from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationError, ConflictError, InvalidStateError, NotFoundError
from app.models.anomaly import Anomaly
from app.models.enums import AnomalyStatus, InspectionStatus
from app.models.inspection import Inspection
from app.repositories.inspection_repository import InspectionRepository
from app.repositories.site_repository import SiteRepository
from app.schemas.inspection import InspectionCreate, InspectionRead, InspectionUpdate
from app.schemas.pagination import Page, page_response
from app.services.risk_service import RiskService

ALLOWED_INSPECTION_TRANSITIONS: dict[InspectionStatus, set[InspectionStatus]] = {
    InspectionStatus.SCHEDULED: {InspectionStatus.IN_PROGRESS, InspectionStatus.CANCELLED},
    InspectionStatus.IN_PROGRESS: {InspectionStatus.COMPLETED, InspectionStatus.CANCELLED},
    InspectionStatus.COMPLETED: set(),
    InspectionStatus.CANCELLED: set(),
}


class InspectionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.inspections = InspectionRepository(session)
        self.sites = SiteRepository(session)

    def get(self, inspection_id: UUID) -> Inspection:
        inspection = self.inspections.get(inspection_id)
        if inspection is None:
            raise NotFoundError("Inspection was not found.", code="inspection_not_found")
        return inspection

    def list(
        self,
        *,
        page: int,
        page_size: int,
        site_id: UUID | None = None,
        status: InspectionStatus | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "inspected_at_desc",
    ) -> Page[InspectionRead]:
        if site_id and self.sites.get(site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        if date_from and date_to and date_from > date_to:
            raise ApplicationError("date_from must be before date_to.", code="invalid_date_range")
        items, total = self.inspections.list(
            page=page,
            page_size=page_size,
            site_id=site_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
        )
        return page_response(
            [InspectionRead.model_validate(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    def list_for_site(self, site_id: UUID, *, page: int, page_size: int) -> Page[InspectionRead]:
        if self.sites.get(site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        return self.list(page=page, page_size=page_size, site_id=site_id)

    def create(self, data: InspectionCreate) -> Inspection:
        if self.sites.get(data.site_id) is None:
            raise NotFoundError("Site was not found.", code="site_not_found")
        inspection = Inspection(
            site_id=data.site_id,
            inspected_at=data.inspected_at,
            status=data.status,
            notes=data.notes,
        )
        inspection.anomalies = [
            Anomaly(
                site_id=data.site_id,
                title=anomaly.title,
                description=anomaly.description,
                severity=anomaly.severity,
                status=AnomalyStatus.OPEN,
                resolved_at=None,
            )
            for anomaly in data.anomalies
        ]
        try:
            self.inspections.add(inspection)
            RiskService(self.session).recalculate(data.site_id)
            self.session.commit()
        except IntegrityError as exception:
            self.session.rollback()
            raise ConflictError(
                "The inspection could not be created because related data changed.",
                code="inspection_create_conflict",
            ) from exception
        return self.get(inspection.id)

    def update(self, inspection_id: UUID, data: InspectionUpdate) -> Inspection:
        inspection = self.get(inspection_id)
        changes = data.model_dump(exclude_unset=True)
        risk_relevant_change = bool({"status", "inspected_at"} & changes.keys())
        next_status = changes.get("status")
        if (
            next_status
            and next_status != inspection.status
            and next_status not in ALLOWED_INSPECTION_TRANSITIONS[inspection.status]
        ):
            raise InvalidStateError(
                f"Inspection cannot move from {inspection.status} to {next_status}.",
                code="invalid_inspection_transition",
            )
        for field, value in changes.items():
            setattr(inspection, field, value)
        if risk_relevant_change:
            RiskService(self.session).recalculate(inspection.site_id)
        self.session.commit()
        return self.get(inspection_id)
