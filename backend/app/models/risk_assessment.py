from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import RiskLevel

if TYPE_CHECKING:
    from app.models.site import Site


class RiskAssessment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="score_range"),
        Index("ix_risk_assessments_site_calculated", "site_id", "calculated_at"),
    )

    site_id: Mapped[UUID] = mapped_column(
        ForeignKey("sites.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", create_constraint=False), nullable=False
    )
    formula_version: Mapped[str] = mapped_column(String(50), nullable=False)
    factor_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    site: Mapped["Site"] = relationship(back_populates="risk_assessments")
