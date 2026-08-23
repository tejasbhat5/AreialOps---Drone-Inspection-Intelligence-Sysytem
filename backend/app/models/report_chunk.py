from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.inspection_report import InspectionReport


class ReportChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_chunks"
    __table_args__ = (
        UniqueConstraint("report_id", "chunk_index", name="uq_report_chunks_report_index"),
        Index("ix_report_chunks_report_id", "report_id"),
    )

    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspection_reports.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | dict[str, Any]] = mapped_column(JSON, nullable=False)

    report: Mapped["InspectionReport"] = relationship(back_populates="chunks")
