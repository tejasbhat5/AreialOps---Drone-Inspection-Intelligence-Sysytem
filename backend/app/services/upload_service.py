from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ApplicationError, ConflictError, PayloadTooLargeError
from app.models.enums import JobStatus, JobType, ReportIngestionStatus
from app.models.inspection_image import InspectionImage
from app.models.inspection_report import InspectionReport
from app.models.processing_job import ProcessingJob
from app.repositories.upload_repository import UploadRepository
from app.services.inspection_service import InspectionService

IMAGE_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"II*\x00", "image/tiff", ".tif"),
    (b"MM\x00*", "image/tiff", ".tif"),
)
IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/tiff"}
REPORT_CONTENT_TYPES = {"application/pdf"}
CHUNK_SIZE = 1024 * 1024


class UploadService:
    def __init__(self, session: Session, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.uploads = UploadRepository(session)
        self.inspections = InspectionService(session)
        self.storage_root = Path(self.settings.upload_directory).resolve()

    @staticmethod
    def _safe_filename(upload: UploadFile) -> str:
        filename = (upload.filename or "").strip()
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            raise ApplicationError(
                "The upload filename is invalid.", code="invalid_upload_filename"
            )
        if len(filename) > 255:
            raise ApplicationError(
                "The upload filename is too long.", code="invalid_upload_filename"
            )
        return filename

    @staticmethod
    def _detect_image_type(header: bytes) -> tuple[str, str] | None:
        for signature, content_type, extension in IMAGE_SIGNATURES:
            if header.startswith(signature):
                return content_type, extension
        return None

    async def _store(
        self,
        upload: UploadFile,
        *,
        category: str,
        max_bytes: int,
        expected_type: str,
        extension: str,
    ) -> tuple[str, int, Path]:
        key = f"{category}/{uuid4()}{extension}"
        destination = self.storage_root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with destination.open("xb") as output:
                while chunk := await upload.read(CHUNK_SIZE):
                    size += len(chunk)
                    if size > max_bytes:
                        raise PayloadTooLargeError(
                            f"Upload exceeds the {max_bytes // (1024 * 1024)} MB limit.",
                            code="upload_too_large",
                        )
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()
        if size == 0:
            destination.unlink(missing_ok=True)
            raise ApplicationError("Empty files cannot be uploaded.", code="empty_upload")
        return key, size, destination

    async def upload_images(
        self, inspection_id: UUID, files: list[UploadFile]
    ) -> tuple[list[InspectionImage], list[ProcessingJob]]:
        self.inspections.get(inspection_id)
        if not files or len(files) > self.settings.max_images_per_request:
            raise ApplicationError(
                f"Upload between 1 and {self.settings.max_images_per_request} images.",
                code="invalid_image_count",
            )
        stored_paths: list[Path] = []
        images: list[InspectionImage] = []
        jobs: list[ProcessingJob] = []
        try:
            for upload in files:
                filename = self._safe_filename(upload)
                header = await upload.read(16)
                await upload.seek(0)
                detected = self._detect_image_type(header)
                declared = (upload.content_type or "").lower()
                if (
                    detected is None
                    or declared not in IMAGE_CONTENT_TYPES
                    or declared != detected[0]
                ):
                    raise ApplicationError(
                        "Image content does not match an allowed JPEG, PNG, or TIFF type.",
                        code="invalid_image_type",
                    )
                key, size, path = await self._store(
                    upload,
                    category="images",
                    max_bytes=self.settings.max_image_upload_bytes,
                    expected_type=detected[0],
                    extension=detected[1],
                )
                stored_paths.append(path)
                image = self.uploads.add_image(
                    InspectionImage(
                        inspection_id=inspection_id,
                        storage_key=key,
                        original_filename=filename,
                        content_type=detected[0],
                        size_bytes=size,
                    )
                )
                job = self.uploads.add_job(
                    ProcessingJob(
                        job_type=JobType.IMAGE_ANALYSIS,
                        status=JobStatus.PENDING,
                        image_id=image.id,
                    )
                )
                images.append(image)
                jobs.append(job)
            self.session.commit()
        except Exception:
            self.session.rollback()
            for path in stored_paths:
                path.unlink(missing_ok=True)
            raise
        return images, jobs

    async def upload_report(
        self, inspection_id: UUID, upload: UploadFile
    ) -> tuple[InspectionReport, ProcessingJob]:
        self.inspections.get(inspection_id)
        if self.uploads.report_for_inspection(inspection_id):
            raise ConflictError(
                "This inspection already has a report.", code="inspection_report_exists"
            )
        filename = self._safe_filename(upload)
        header = await upload.read(5)
        await upload.seek(0)
        declared = (upload.content_type or "").lower()
        if header != b"%PDF-" or declared not in REPORT_CONTENT_TYPES:
            raise ApplicationError(
                "Inspection reports must be valid PDF files.", code="invalid_report_type"
            )
        key, size, path = await self._store(
            upload,
            category="reports",
            max_bytes=self.settings.max_report_upload_bytes,
            expected_type="application/pdf",
            extension=".pdf",
        )
        try:
            report = self.uploads.add_report(
                InspectionReport(
                    inspection_id=inspection_id,
                    storage_key=key,
                    original_filename=filename,
                    content_type="application/pdf",
                    size_bytes=size,
                    ingestion_status=ReportIngestionStatus.PENDING,
                )
            )
            job = self.uploads.add_job(
                ProcessingJob(
                    job_type=JobType.REPORT_INGESTION,
                    status=JobStatus.PENDING,
                    report_id=report.id,
                )
            )
            self.session.commit()
        except IntegrityError as exception:
            self.session.rollback()
            path.unlink(missing_ok=True)
            raise ConflictError(
                "This inspection already has a report.", code="inspection_report_exists"
            ) from exception
        except Exception:
            self.session.rollback()
            path.unlink(missing_ok=True)
            raise
        return report, job

    def list_images(self, inspection_id: UUID) -> list[InspectionImage]:
        self.inspections.get(inspection_id)
        return self.uploads.images_for_inspection(inspection_id)

    def get_report(self, inspection_id: UUID) -> InspectionReport | None:
        self.inspections.get(inspection_id)
        return self.uploads.report_for_inspection(inspection_id)

    def list_jobs(self, inspection_id: UUID) -> list[ProcessingJob]:
        self.inspections.get(inspection_id)
        return self.uploads.jobs_for_inspection(inspection_id)
