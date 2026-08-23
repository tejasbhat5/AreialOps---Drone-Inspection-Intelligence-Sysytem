from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.site import Site
from app.rag.chunker import ReportChunker
from app.rag.embedding_service import LocalHashEmbeddingService
from app.rag.retrieval_service import ReportRetrievalService
from scripts.seed_demo_data import seed_demo_data


def test_local_embeddings_are_deterministic_and_rank_related_text() -> None:
    service = LocalHashEmbeddingService()
    query = service.embed("solar thermal hotspot")
    related = service.embed("solar panel thermal hotspot requires inspection")
    unrelated = service.embed("rail bridge access route")

    assert query == service.embed("solar thermal hotspot")
    assert service.similarity(query, related) > service.similarity(query, unrelated)


def test_report_chunker_uses_bounded_overlap() -> None:
    chunks = ReportChunker(chunk_words=50, overlap_words=10).chunk(
        " ".join(f"word-{index}" for index in range(95))
    )

    assert len(chunks) == 3
    assert chunks[0].content.split()[-10:] == chunks[1].content.split()[:10]


def test_seeded_reports_are_retrievable_with_source_citations(db_session: Session) -> None:
    seed_demo_data(db_session, now=datetime(2026, 8, 22, 12, tzinfo=UTC))
    alpha = db_session.query(Site).filter(Site.name == "Solar Farm Alpha").one()

    result = ReportRetrievalService(db_session).search(
        "What condition was recorded in the previous inspection?",
        site_id=alpha.id,
        limit=3,
    )

    assert result.total == 1
    assert result.citations[0].site_name == "Solar Farm Alpha"
    assert "Previous inspection report" in result.citations[0].excerpt
