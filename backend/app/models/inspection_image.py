from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, BigInteger, CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ImageReviewStatus

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.processing_job import ProcessingJob


class InspectionImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inspection_images"
    __table_args__ = (CheckConstraint("size_bytes > 0", name="positive_size"),)

    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    review_status: Mapped[ImageReviewStatus] = mapped_column(
        Enum(ImageReviewStatus, name="image_review_status"),
        default=ImageReviewStatus.NOT_ANALYZED,
        nullable=False,
    )
    ai_findings: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    inspection: Mapped["Inspection"] = relationship(back_populates="images")
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
