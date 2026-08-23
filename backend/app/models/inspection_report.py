from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ReportIngestionStatus

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.processing_job import ProcessingJob
    from app.models.report_chunk import ReportChunk


class InspectionReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inspection_reports"
    __table_args__ = (CheckConstraint("size_bytes > 0", name="positive_size"),)

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    ingestion_status: Mapped[ReportIngestionStatus] = mapped_column(
        Enum(ReportIngestionStatus, name="report_ingestion_status"),
        default=ReportIngestionStatus.NOT_STARTED,
        nullable=False,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    inspection: Mapped["Inspection"] = relationship(back_populates="report")
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    chunks: Mapped[list["ReportChunk"]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportChunk.chunk_index"
    )
