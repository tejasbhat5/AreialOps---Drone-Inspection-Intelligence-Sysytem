from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import DatabaseSession
from app.models.enums import InspectionStatus, RiskLevel, SiteStatus, SiteType
from app.schemas.anomaly import AnomalyRead
from app.schemas.inspection import InspectionRead
from app.schemas.pagination import Page
from app.schemas.risk import RiskAssessmentRead
from app.schemas.site import SiteCreate, SiteDetail, SiteRead, SiteUpdate
from app.services.anomaly_service import AnomalyService
from app.services.inspection_service import InspectionService
from app.services.risk_service import RiskService
from app.services.site_service import SiteService

router = APIRouter(prefix="/api/sites")


@router.get("", response_model=Page[SiteRead])
def list_sites(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    query: Annotated[str | None, Query(min_length=1, max_length=150)] = None,
    site_type: SiteType | None = None,
    site_status: Annotated[SiteStatus | None, Query(alias="status")] = None,
    risk_level: Annotated[list[RiskLevel] | None, Query()] = None,
    inspection_status: InspectionStatus | None = None,
    sort: Literal["name", "risk_desc", "created_at_desc"] = "name",
) -> Page[SiteRead]:
    return SiteService(session).list(
        page=page,
        page_size=page_size,
        query=query,
        site_type=site_type,
        status=site_status,
        risk_levels=risk_level,
        inspection_status=inspection_status,
        sort=sort,
    )


@router.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def create_site(data: SiteCreate, session: DatabaseSession) -> SiteRead:
    return SiteRead.model_validate(SiteService(session).create(data))


@router.get("/{site_id}", response_model=SiteDetail)
def get_site(site_id: UUID, session: DatabaseSession) -> SiteDetail:
    return SiteService(session).get_detail(site_id)


@router.patch("/{site_id}", response_model=SiteRead)
def update_site(site_id: UUID, data: SiteUpdate, session: DatabaseSession) -> SiteRead:
    return SiteRead.model_validate(SiteService(session).update(site_id, data))


@router.get("/{site_id}/inspections", response_model=Page[InspectionRead])
def list_site_inspections(
    site_id: UUID,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Page[InspectionRead]:
    return InspectionService(session).list_for_site(site_id, page=page, page_size=page_size)


@router.get("/{site_id}/anomalies", response_model=Page[AnomalyRead])
def list_site_anomalies(
    site_id: UUID,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    unresolved_only: bool = False,
) -> Page[AnomalyRead]:
    return AnomalyService(session).list(
        page=page,
        page_size=page_size,
        site_id=site_id,
        unresolved_only=unresolved_only,
    )


@router.get("/{site_id}/risk", response_model=RiskAssessmentRead | None)
def get_site_risk(site_id: UUID, session: DatabaseSession) -> RiskAssessmentRead | None:
    assessment = RiskService(session).latest(site_id)
    return RiskAssessmentRead.model_validate(assessment) if assessment else None


@router.get("/{site_id}/risk/history", response_model=list[RiskAssessmentRead])
def get_site_risk_history(
    site_id: UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[RiskAssessmentRead]:
    return [
        RiskAssessmentRead.model_validate(item)
        for item in RiskService(session).history(site_id, limit=limit)
    ]


@router.post("/{site_id}/risk/recalculate", response_model=RiskAssessmentRead)
def recalculate_site_risk(site_id: UUID, session: DatabaseSession) -> RiskAssessmentRead:
    assessment = RiskService(session).recalculate(site_id)
    session.commit()
    return RiskAssessmentRead.model_validate(assessment)
