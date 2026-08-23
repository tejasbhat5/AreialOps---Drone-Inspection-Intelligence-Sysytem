import re

from app.rag.schemas import TextChunk


class ReportChunker:
    def __init__(self, *, chunk_words: int = 180, overlap_words: int = 35) -> None:
        if chunk_words < 50 or overlap_words < 0 or overlap_words >= chunk_words:
            raise ValueError("Invalid report chunking configuration.")
        self.chunk_words = chunk_words
        self.overlap_words = overlap_words

    def chunk(self, text: str) -> list[TextChunk]:
        cleaned = re.sub(r"\s+", " ", text).strip()
        words = cleaned.split()
        if not words:
            return []
        step = self.chunk_words - self.overlap_words
        chunks: list[TextChunk] = []
        for start in range(0, len(words), step):
            content_words = words[start : start + self.chunk_words]
            if not content_words:
                break
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=" ".join(content_words),
                    token_count=len(content_words),
                )
            )
            if start + self.chunk_words >= len(words):
                break
        return chunks
