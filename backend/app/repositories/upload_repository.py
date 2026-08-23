from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inspection_image import InspectionImage
from app.models.inspection_report import InspectionReport
from app.models.processing_job import ProcessingJob


class UploadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_image(self, image: InspectionImage) -> InspectionImage:
        self.session.add(image)
        self.session.flush()
        return image

    def add_report(self, report: InspectionReport) -> InspectionReport:
        self.session.add(report)
        self.session.flush()
        return report

    def add_job(self, job: ProcessingJob) -> ProcessingJob:
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, job_id: UUID) -> ProcessingJob | None:
        return self.session.get(ProcessingJob, job_id)

    def report_for_inspection(self, inspection_id: UUID) -> InspectionReport | None:
        return self.session.scalar(
            select(InspectionReport).where(InspectionReport.inspection_id == inspection_id)
        )

    def images_for_inspection(self, inspection_id: UUID) -> list[InspectionImage]:
        return list(
            self.session.scalars(
                select(InspectionImage)
                .where(InspectionImage.inspection_id == inspection_id)
                .order_by(InspectionImage.created_at.desc())
            )
        )

    def jobs_for_inspection(self, inspection_id: UUID) -> list[ProcessingJob]:
        return list(
            self.session.scalars(
                select(ProcessingJob)
                .outerjoin(InspectionReport, ProcessingJob.report_id == InspectionReport.id)
                .outerjoin(InspectionImage, ProcessingJob.image_id == InspectionImage.id)
                .where(
                    (InspectionReport.inspection_id == inspection_id)
                    | (InspectionImage.inspection_id == inspection_id)
                )
                .order_by(ProcessingJob.created_at.desc())
            )
        )
