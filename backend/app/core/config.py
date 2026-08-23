from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AERIALOPS_",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = "development"
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:3000"
    api_host: str = "127.0.0.1"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = (
        "postgresql+psycopg://aerialops:aerialops@127.0.0.1:5432/aerialops?connect_timeout=2"
    )
    upload_directory: str = "storage/uploads"
    max_image_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1)
    max_report_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    max_images_per_request: int = Field(default=10, ge=1, le=50)
    agent_provider: str = "deterministic"
    agent_model: str = "gemini-3.1-flash-lite"
    agent_timeout_seconds: float = Field(default=20.0, ge=1, le=60)
    agent_max_output_tokens: int = Field(default=900, ge=200, le=4_000)
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AERIALOPS_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AERIALOPS_GEMINI_API_KEY", "GEMINI_API_KEY"),
    )
    vision_provider: str = "disabled"
    vision_model: str = "gemini-3.1-flash-lite"


@lru_cache
def get_settings() -> Settings:
    """Create one immutable settings object per application process."""
    return Settings()
