from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.enums import ReportIngestionStatus
from app.rag.schemas import ReportCitation
from app.schemas.base import ORMModel


class ReportRecord(ORMModel):
    id: UUID
    inspection_id: UUID
    site_id: UUID
    site_name: str
    original_filename: str
    ingestion_status: ReportIngestionStatus
    chunk_count: int = Field(ge=0)
    created_at: datetime


class ReportSearchRequest(ORMModel):
    query: str = Field(min_length=2, max_length=500)
    site_id: UUID | None = None
    limit: int = Field(default=5, ge=1, le=10)


class ReportSearchResponse(ORMModel):
    query: str
    citations: list[ReportCitation]
    total: int = Field(ge=0)
