from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.models.enums import InspectionStatus
from app.schemas.anomaly import AnomalyCreate, AnomalyRead
from app.schemas.base import ORMModel


class InspectionCreate(ORMModel):
    site_id: UUID
    inspected_at: datetime
    status: InspectionStatus
    notes: str | None = Field(default=None, max_length=20_000)
    anomalies: list[AnomalyCreate] = Field(default_factory=list, max_length=100)

    @field_validator("inspected_at")
    @classmethod
    def inspected_at_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("inspected_at must include a timezone")
        return value


class InspectionRead(ORMModel):
    id: UUID
    site_id: UUID
    inspected_at: datetime
    status: InspectionStatus
    notes: str | None
    anomalies: list[AnomalyRead]
    created_at: datetime
    updated_at: datetime


class InspectionUpdate(ORMModel):
    inspected_at: datetime | None = None
    status: InspectionStatus | None = None
    notes: str | None = Field(default=None, max_length=20_000)

    @field_validator("inspected_at")
    @classmethod
    def updated_inspected_at_has_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("inspected_at must include a timezone")
        return value
