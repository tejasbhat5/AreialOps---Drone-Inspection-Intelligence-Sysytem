from uuid import UUID

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import DatabaseSession
from app.core.exceptions import ConflictError, NotFoundError
from app.jobs.runner import process_job
from app.models.enums import JobStatus
from app.repositories.upload_repository import UploadRepository
from app.schemas.jobs import ProcessingJobRead

router = APIRouter(prefix="/api/jobs")


@router.get("/{job_id}", response_model=ProcessingJobRead)
def get_job(job_id: UUID, session: DatabaseSession) -> ProcessingJobRead:
    job = UploadRepository(session).get_job(job_id)
    if job is None:
        raise NotFoundError("Processing job was not found.", code="job_not_found")
    return ProcessingJobRead.model_validate(job)


@router.post("/{job_id}/retry", response_model=ProcessingJobRead)
def retry_job(
    job_id: UUID, session: DatabaseSession, background_tasks: BackgroundTasks
) -> ProcessingJobRead:
    job = UploadRepository(session).get_job(job_id)
    if job is None:
        raise NotFoundError("Processing job was not found.", code="job_not_found")
    if job.status != JobStatus.FAILED:
        raise ConflictError("Only failed jobs can be retried.", code="job_not_failed")
    job.status = JobStatus.PENDING
    session.commit()
    factory = sessionmaker(bind=session.get_bind(), autoflush=False, expire_on_commit=False)
    background_tasks.add_task(process_job, job.id, factory)
    return ProcessingJobRead.model_validate(job)
