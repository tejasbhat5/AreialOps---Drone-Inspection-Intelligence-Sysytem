from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InspectionStatus

if TYPE_CHECKING:
    from app.models.anomaly import Anomaly
    from app.models.inspection_image import InspectionImage
    from app.models.inspection_report import InspectionReport
    from app.models.site import Site


class Inspection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inspections"
    __table_args__ = (
        Index("ix_inspections_site_inspected_at", "site_id", "inspected_at"),
        Index("ix_inspections_status_inspected_at", "status", "inspected_at"),
    )

    site_id: Mapped[UUID] = mapped_column(
        ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False
    )
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[InspectionStatus] = mapped_column(
        Enum(InspectionStatus, name="inspection_status"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    site: Mapped["Site"] = relationship(back_populates="inspections")
    images: Mapped[list["InspectionImage"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )
    anomalies: Mapped[list["Anomaly"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )
    report: Mapped["InspectionReport | None"] = relationship(
        back_populates="inspection", cascade="all, delete-orphan", uselist=False
    )
