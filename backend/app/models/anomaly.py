from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AnomalySeverity, AnomalyStatus

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.site import Site


class Anomaly(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "anomalies"
    __table_args__ = (
        CheckConstraint(
            "(status = 'RESOLVED' AND resolved_at IS NOT NULL) OR "
            "(status <> 'RESOLVED' AND resolved_at IS NULL)",
            name="resolved_at_matches_status",
        ),
        Index("ix_anomalies_site_status_severity", "site_id", "status", "severity"),
        Index("ix_anomalies_status_created_at", "status", "created_at"),
    )

    site_id: Mapped[UUID] = mapped_column(
        ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False
    )
    inspection_id: Mapped[UUID] = mapped_column(
        ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[AnomalySeverity] = mapped_column(
        Enum(AnomalySeverity, name="anomaly_severity"), nullable=False
    )
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus, name="anomaly_status"),
        default=AnomalyStatus.OPEN,
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["Site"] = relationship(back_populates="anomalies")
    inspection: Mapped["Inspection"] = relationship(back_populates="anomalies")
