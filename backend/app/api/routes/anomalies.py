from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.models.enums import AnomalySeverity, AnomalyStatus
from app.schemas.anomaly import AnomalyRead, AnomalyUpdate
from app.schemas.pagination import Page
from app.services.anomaly_service import AnomalyService

router = APIRouter(prefix="/api/anomalies")


@router.get("", response_model=Page[AnomalyRead])
def list_anomalies(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    site_id: UUID | None = None,
    inspection_id: UUID | None = None,
    severity: AnomalySeverity | None = None,
    anomaly_status: Annotated[AnomalyStatus | None, Query(alias="status")] = None,
    unresolved_only: bool = False,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> Page[AnomalyRead]:
    return AnomalyService(session).list(
        page=page,
        page_size=page_size,
        site_id=site_id,
        inspection_id=inspection_id,
        severity=severity,
        status=anomaly_status,
        unresolved_only=unresolved_only,
        created_from=created_from,
        created_to=created_to,
    )


@router.get("/{anomaly_id}", response_model=AnomalyRead)
def get_anomaly(anomaly_id: UUID, session: DatabaseSession) -> AnomalyRead:
    return AnomalyRead.model_validate(AnomalyService(session).get(anomaly_id))


@router.patch("/{anomaly_id}", response_model=AnomalyRead)
def update_anomaly(anomaly_id: UUID, data: AnomalyUpdate, session: DatabaseSession) -> AnomalyRead:
    return AnomalyRead.model_validate(AnomalyService(session).update(anomaly_id, data))
