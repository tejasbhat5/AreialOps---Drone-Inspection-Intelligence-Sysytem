from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import AnomalySeverity, AnomalyStatus
from app.schemas.base import ORMModel


class AnomalyCreate(ORMModel):
    title: str = Field(min_length=1, max_length=180)
    description: str = Field(min_length=1, max_length=10_000)
    severity: AnomalySeverity


class AnomalyRead(AnomalyCreate):
    id: UUID
    site_id: UUID
    inspection_id: UUID
    status: AnomalyStatus
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnomalyUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, min_length=1, max_length=10_000)
    severity: AnomalySeverity | None = None
    status: AnomalyStatus | None = None
