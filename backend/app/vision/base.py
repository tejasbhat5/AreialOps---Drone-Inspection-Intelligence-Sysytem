from pathlib import Path
from typing import Protocol

from app.vision.schemas import VisionAnalysis


class VisionAnalyzer(Protocol):
    def analyze(self, path: Path, content_type: str) -> VisionAnalysis: ...
