from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RiskLevel, SiteStatus, SiteType

if TYPE_CHECKING:
    from app.models.agent_conversation import AgentConversation
    from app.models.anomaly import Anomaly
    from app.models.inspection import Inspection
    from app.models.risk_assessment import RiskAssessment


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sites"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="latitude_range"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="longitude_range"),
        CheckConstraint(
            "current_risk_score >= 0 AND current_risk_score <= 100",
            name="current_risk_score_range",
        ),
        Index("ix_sites_site_type", "site_type"),
        Index("ix_sites_status_risk", "status", "current_risk_level"),
        Index("ix_sites_coordinates", "latitude", "longitude"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    site_type: Mapped[SiteType] = mapped_column(Enum(SiteType, name="site_type"), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    status: Mapped[SiteStatus] = mapped_column(
        Enum(SiteStatus, name="site_status"), default=SiteStatus.ACTIVE, nullable=False
    )
    current_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"), default=RiskLevel.LOW, nullable=False
    )

    inspections: Mapped[list["Inspection"]] = relationship(back_populates="site")
    anomalies: Mapped[list["Anomaly"]] = relationship(back_populates="site")
    risk_assessments: Mapped[list["RiskAssessment"]] = relationship(back_populates="site")
    agent_conversations: Mapped[list["AgentConversation"]] = relationship(back_populates="site")


Index("uq_sites_name_lower", func.lower(Site.name), unique=True)
