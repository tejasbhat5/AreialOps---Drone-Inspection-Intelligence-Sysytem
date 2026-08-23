import hashlib
import math
import re


class LocalHashEmbeddingService:
    """Deterministic zero-secret embeddings suitable for an explainable local MVP."""

    def __init__(self, dimensions: int = 192) -> None:
        if dimensions < 32:
            raise ValueError("Embedding dimensions must be at least 32.")
        self.dimensions = dimensions

    @staticmethod
    def tokens(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = self.tokens(text)
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [round(value / magnitude, 8) for value in vector] if magnitude else vector

    @staticmethod
    def similarity(first: list[float], second: list[float]) -> float:
        if len(first) != len(second):
            return 0.0
        return max(0.0, min(1.0, sum(a * b for a, b in zip(first, second, strict=True))))
