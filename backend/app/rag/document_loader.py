from pathlib import Path

from app.core.exceptions import ApplicationError


class ReportDocumentLoader:
    def extract(self, path: Path, content_type: str) -> str:
        if content_type == "text/plain":
            return path.read_text(encoding="utf-8")
        if content_type != "application/pdf":
            raise ApplicationError("Unsupported report format.", code="unsupported_report_format")
        try:
            from pypdf import PdfReader
        except ImportError as exception:
            raise ApplicationError(
                "PDF extraction support is unavailable.", code="pdf_extractor_unavailable"
            ) from exception
        try:
            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exception:
            raise ApplicationError(
                "The report could not be parsed.", code="report_extraction_failed"
            ) from exception
