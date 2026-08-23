from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.models.enums import ImageReviewStatus, JobStatus, JobType, ReportIngestionStatus
from app.models.processing_job import ProcessingJob
from app.models.report_chunk import ReportChunk
from app.rag.chunker import ReportChunker
from app.rag.document_loader import ReportDocumentLoader
from app.rag.embedding_service import LocalHashEmbeddingService
from app.rag.vector_repository import ReportVectorRepository
from app.vision.analyzer import build_vision_analyzer

logger = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def process_job(job_id: UUID, session_factory=None) -> None:
    factory = session_factory or get_session_factory()
    with factory() as session:
        job = session.get(ProcessingJob, job_id)
        if job is None or job.status not in {JobStatus.PENDING, JobStatus.FAILED}:
            return
        job.status = JobStatus.PROCESSING
        job.started_at = _now()
        job.attempts += 1
        job.error_code = None
        job.error_message = None
        session.commit()
        try:
            if job.job_type == JobType.REPORT_INGESTION:
                _process_report(session, job)
            else:
                _process_image(session, job)
            job.status = JobStatus.COMPLETED
            job.completed_at = _now()
            session.commit()
            logger.info(
                "background_job_completed",
                extra={"job_id": str(job.id), "job_type": job.job_type.value},
            )
        except Exception as exception:
            session.rollback()
            failed_job = session.get(ProcessingJob, job_id)
            if failed_job is not None:
                failed_job.status = JobStatus.FAILED
                failed_job.completed_at = _now()
                failed_job.error_code = getattr(exception, "code", "job_processing_failed")
                failed_job.error_message = "Background processing failed safely."
                if failed_job.report:
                    failed_job.report.ingestion_status = ReportIngestionStatus.FAILED
                session.commit()
            logger.exception(
                "background_job_failed",
                extra={"job_id": str(job_id), "error_code": getattr(exception, "code", None)},
            )


def _process_report(session, job: ProcessingJob) -> None:
    report = job.report
    if report is None:
        raise ValueError("Report job has no report.")
    report.ingestion_status = ReportIngestionStatus.PROCESSING
    session.flush()
    settings = get_settings()
    path = Path(settings.upload_directory).resolve() / report.storage_key
    text = report.extracted_text or ReportDocumentLoader().extract(path, report.content_type)
    chunks = ReportChunker().chunk(text)
    if not chunks:
        raise ValueError("Report contains no searchable text.")
    embeddings = LocalHashEmbeddingService()
    ReportVectorRepository(session).replace(
        report.id,
        [
            ReportChunk(
                report_id=report.id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                embedding=embeddings.embed(chunk.content),
            )
            for chunk in chunks
        ],
    )
    report.extracted_text = text
    report.ingestion_status = ReportIngestionStatus.COMPLETED


def _process_image(session, job: ProcessingJob) -> None:
    image = job.image
    if image is None:
        raise ValueError("Image job has no image.")
    settings = get_settings()
    path = Path(settings.upload_directory).resolve() / image.storage_key
    result = build_vision_analyzer(settings).analyze(path, image.content_type)
    image.ai_findings = result.model_dump(mode="json")
    image.review_status = (
        ImageReviewStatus.PENDING_REVIEW
        if result.status == "completed"
        else ImageReviewStatus.NOT_ANALYZED
    )
