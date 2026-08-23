from datetime import datetime
from uuid import UUID

from app.models.enums import JobStatus, JobType
from app.schemas.base import ORMModel


class ProcessingJobRead(ORMModel):
    id: UUID
    job_type: JobType
    status: JobStatus
    report_id: UUID | None
    image_id: UUID | None
    attempts: int
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
