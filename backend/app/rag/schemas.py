from uuid import UUID

from pydantic import Field

from app.schemas.base import ORMModel


class TextChunk(ORMModel):
    index: int = Field(ge=0)
    content: str = Field(min_length=1)
    token_count: int = Field(ge=1)


class ReportCitation(ORMModel):
    report_id: UUID
    inspection_id: UUID
    site_id: UUID
    site_name: str
    report_filename: str
    chunk_index: int = Field(ge=0)
    excerpt: str
    score: float = Field(ge=0, le=1)


class ReportSearchResults(ORMModel):
    query: str
    citations: list[ReportCitation]
    total: int = Field(ge=0)
