from typing import Literal

from pydantic import Field

from app.schemas.base import ORMModel


class VisionFinding(ORMModel):
    label: str
    description: str
    confidence: float = Field(ge=0, le=1)


class VisionAnalysis(ORMModel):
    status: Literal["completed", "not_configured"]
    provider: str
    findings: list[VisionFinding] = Field(default_factory=list, max_length=10)
    limitation: str
