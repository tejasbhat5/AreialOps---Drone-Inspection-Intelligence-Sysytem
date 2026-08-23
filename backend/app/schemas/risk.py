from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.models.enums import RiskLevel
from app.schemas.base import ORMModel


class RiskAssessmentRead(ORMModel):
    id: UUID
    site_id: UUID
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    formula_version: str
    factor_snapshot: dict[str, Any]
    calculated_at: datetime
