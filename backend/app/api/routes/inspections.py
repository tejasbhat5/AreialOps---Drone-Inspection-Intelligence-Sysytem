from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Query, UploadFile, status
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import DatabaseSession
from app.jobs.runner import process_job
from app.models.enums import InspectionStatus
from app.schemas.anomaly import AnomalyCreate, AnomalyRead
from app.schemas.inspection import InspectionCreate, InspectionRead, InspectionUpdate
from app.schemas.jobs import ProcessingJobRead
from app.schemas.pagination import Page
from app.schemas.uploads import (
    ImageUploadResponse,
    InspectionImageRead,
    InspectionReportRead,
    ReportUploadResponse,
)
from app.services.anomaly_service import AnomalyService
from app.services.inspection_service import InspectionService
from app.services.upload_service import UploadService

router = APIRouter(prefix="/api/inspections")


@router.get("", response_model=Page[InspectionRead])
def list_inspections(
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    site_id: UUID | None = None,
    inspection_status: Annotated[InspectionStatus | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: Literal["inspected_at_desc", "inspected_at_asc"] = "inspected_at_desc",
) -> Page[InspectionRead]:
    return InspectionService(session).list(
        page=page,
        page_size=page_size,
        site_id=site_id,
        status=inspection_status,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )


@router.post("", response_model=InspectionRead, status_code=status.HTTP_201_CREATED)
def create_inspection(data: InspectionCreate, session: DatabaseSession) -> InspectionRead:
    return InspectionRead.model_validate(InspectionService(session).create(data))


@router.get("/{inspection_id}", response_model=InspectionRead)
def get_inspection(inspection_id: UUID, session: DatabaseSession) -> InspectionRead:
    return InspectionRead.model_validate(InspectionService(session).get(inspection_id))


@router.patch("/{inspection_id}", response_model=InspectionRead)
def update_inspection(
    inspection_id: UUID, data: InspectionUpdate, session: DatabaseSession
) -> InspectionRead:
    return InspectionRead.model_validate(InspectionService(session).update(inspection_id, data))


@router.post(
    "/{inspection_id}/anomalies",
    response_model=AnomalyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inspection_anomaly(
    inspection_id: UUID, data: AnomalyCreate, session: DatabaseSession
) -> AnomalyRead:
    anomaly = AnomalyService(session).create_for_inspection(inspection_id, data)
    return AnomalyRead.model_validate(anomaly)


@router.get("/{inspection_id}/images", response_model=list[InspectionImageRead])
def list_inspection_images(
    inspection_id: UUID, session: DatabaseSession
) -> list[InspectionImageRead]:
    return [
        InspectionImageRead.model_validate(item)
        for item in UploadService(session).list_images(inspection_id)
    ]


@router.post(
    "/{inspection_id}/images",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_inspection_images(
    inspection_id: UUID,
    session: DatabaseSession,
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="JPEG, PNG, or TIFF images")],
) -> ImageUploadResponse:
    images, jobs = await UploadService(session).upload_images(inspection_id, files)
    factory = sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
    for job in jobs:
        background_tasks.add_task(process_job, job.id, factory)
    return ImageUploadResponse(
        images=[InspectionImageRead.model_validate(item) for item in images],
        processing_jobs=[ProcessingJobRead.model_validate(item) for item in jobs],
    )


@router.get("/{inspection_id}/report", response_model=InspectionReportRead | None)
def get_inspection_report(
    inspection_id: UUID, session: DatabaseSession
) -> InspectionReportRead | None:
    report = UploadService(session).get_report(inspection_id)
    return InspectionReportRead.model_validate(report) if report else None


@router.post(
    "/{inspection_id}/report",
    response_model=ReportUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_inspection_report(
    inspection_id: UUID,
    session: DatabaseSession,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="PDF inspection report")],
) -> ReportUploadResponse:
    report, job = await UploadService(session).upload_report(inspection_id, file)
    factory = sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
    background_tasks.add_task(process_job, job.id, factory)
    return ReportUploadResponse(
        report=InspectionReportRead.model_validate(report),
        processing_job=ProcessingJobRead.model_validate(job),
    )


@router.get("/{inspection_id}/jobs", response_model=list[ProcessingJobRead])
def list_inspection_jobs(inspection_id: UUID, session: DatabaseSession) -> list[ProcessingJobRead]:
    return [
        ProcessingJobRead.model_validate(item)
        for item in UploadService(session).list_jobs(inspection_id)
    ]
