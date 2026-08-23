from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import RiskLevel, SiteStatus, SiteType
from app.schemas.base import ORMModel


class SiteCreate(ORMModel):
    name: str = Field(min_length=1, max_length=150)
    site_type: SiteType
    location: str = Field(min_length=1, max_length=255)
    latitude: Decimal = Field(ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal = Field(ge=-180, le=180, max_digits=10, decimal_places=6)
    status: SiteStatus = SiteStatus.ACTIVE

    @field_validator("name", "location")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must contain non-whitespace characters")
        return stripped


class SiteRead(SiteCreate):
    id: UUID
    current_risk_score: int = Field(ge=0, le=100)
    current_risk_level: RiskLevel
    created_at: datetime
    updated_at: datetime


class SiteUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    site_type: SiteType | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(
        default=None, ge=-180, le=180, max_digits=10, decimal_places=6
    )
    status: SiteStatus | None = None

    @field_validator("name", "location")
    @classmethod
    def strip_updated_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must contain non-whitespace characters")
        return stripped


class SiteDetail(SiteRead):
    inspection_count: int = Field(ge=0)
    unresolved_anomaly_count: int = Field(ge=0)
