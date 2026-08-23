import base64
from pathlib import Path

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ApplicationError
from app.vision.schemas import VisionAnalysis

VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["completed"]},
        "provider": {"type": "string"},
        "findings": {
            "type": "array",
            "maxItems": 10,
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["label", "description", "confidence"],
            },
        },
        "limitation": {"type": "string"},
    },
    "required": ["status", "provider", "findings", "limitation"],
}


class DisabledVisionAnalyzer:
    def analyze(self, path: Path, content_type: str) -> VisionAnalysis:
        del path, content_type
        return VisionAnalysis(
            status="not_configured",
            provider="disabled",
            limitation=(
                "No image model is configured. AerialOps does not fabricate defect findings."
            ),
        )


class GeminiVisionAnalyzer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze(self, path: Path, content_type: str) -> VisionAnalysis:
        secret = self.settings.gemini_api_key
        api_key = secret.get_secret_value().strip() if secret else ""
        if not api_key:
            raise ApplicationError(
                "Vision provider credentials are unavailable.", code="vision_not_configured"
            )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Perform cautious AI-assisted visual screening. Identify only "
                                "clearly visible possible conditions such as cracks, corrosion, "
                                "vegetation, or surface damage. Do not claim certified industrial "
                                "defect detection."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": content_type,
                                "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": VISION_SCHEMA,
            },
        }
        try:
            response = httpx.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.settings.vision_model}:generateContent",
                headers={"x-goog-api-key": api_key},
                json=payload,
                timeout=self.settings.agent_timeout_seconds,
            )
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            analysis = VisionAnalysis.model_validate_json(text)
            return analysis.model_copy(
                update={
                    "provider": f"gemini:{self.settings.vision_model}",
                    "limitation": (
                        "AI-assisted screening only; every finding requires human review."
                    ),
                }
            )
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exception:
            raise ApplicationError(
                "AI-assisted image analysis failed safely.", code="vision_provider_failed"
            ) from exception


def build_vision_analyzer(settings: Settings | None = None):
    configured = settings or get_settings()
    if configured.vision_provider.lower() == "gemini":
        return GeminiVisionAnalyzer(configured)
    return DisabledVisionAnalyzer()
