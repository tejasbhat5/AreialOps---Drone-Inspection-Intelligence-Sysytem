from uuid import UUID

from sqlalchemy.orm import Session

from app.rag.embedding_service import LocalHashEmbeddingService
from app.rag.schemas import ReportCitation, ReportSearchResults
from app.rag.vector_repository import ReportVectorRepository


class ReportRetrievalService:
    def __init__(self, session: Session) -> None:
        self.vectors = ReportVectorRepository(session)
        self.embeddings = LocalHashEmbeddingService()

    def search(
        self, query: str, *, site_id: UUID | None = None, limit: int = 5
    ) -> ReportSearchResults:
        query_vector = self.embeddings.embed(query)
        ranked = sorted(
            (
                (self.embeddings.similarity(query_vector, list(chunk.embedding)), chunk)
                for chunk in self.vectors.searchable(site_id=site_id)
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        citations: list[ReportCitation] = []
        for score, chunk in ranked[:limit]:
            report = chunk.report
            inspection = report.inspection
            excerpt = chunk.content if len(chunk.content) <= 320 else chunk.content[:317] + "..."
            citations.append(
                ReportCitation(
                    report_id=report.id,
                    inspection_id=inspection.id,
                    site_id=inspection.site_id,
                    site_name=inspection.site.name,
                    report_filename=report.original_filename,
                    chunk_index=chunk.chunk_index,
                    excerpt=excerpt,
                    score=round(score, 4),
                )
            )
        return ReportSearchResults(query=query, citations=citations, total=len(citations))
