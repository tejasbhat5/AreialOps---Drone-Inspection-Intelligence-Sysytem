from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus, JobType

if TYPE_CHECKING:
    from app.models.inspection_image import InspectionImage
    from app.models.inspection_report import InspectionReport


class ProcessingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint(
            "(report_id IS NOT NULL AND image_id IS NULL) OR "
            "(report_id IS NULL AND image_id IS NOT NULL)",
            name="exactly_one_source",
        ),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        Index("ix_processing_jobs_status_created", "status", "created_at"),
    )

    job_type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status"), default=JobStatus.PENDING, nullable=False
    )
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inspection_reports.id", ondelete="CASCADE"), nullable=True, index=True
    )
    image_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inspection_images.id", ondelete="CASCADE"), nullable=True, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    report: Mapped["InspectionReport | None"] = relationship(back_populates="processing_jobs")
    image: Mapped["InspectionImage | None"] = relationship(back_populates="processing_jobs")
