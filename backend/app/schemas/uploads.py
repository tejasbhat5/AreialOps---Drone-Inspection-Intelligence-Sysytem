from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.enums import ImageReviewStatus, ReportIngestionStatus
from app.schemas.base import ORMModel
from app.schemas.jobs import ProcessingJobRead


class InspectionImageRead(ORMModel):
    id: UUID
    inspection_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    review_status: ImageReviewStatus
    ai_findings: dict[str, Any] | None
    created_at: datetime


class InspectionReportRead(ORMModel):
    id: UUID
    inspection_id: UUID
    original_filename: str
    content_type: str
    size_bytes: int
    ingestion_status: ReportIngestionStatus
    created_at: datetime


class ImageUploadResponse(ORMModel):
    images: list[InspectionImageRead]
    processing_jobs: list[ProcessingJobRead]


class ReportUploadResponse(ORMModel):
    report: InspectionReportRead
    processing_job: ProcessingJobRead
