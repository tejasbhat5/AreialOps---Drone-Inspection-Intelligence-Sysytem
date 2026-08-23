from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run process-level startup and shutdown hooks."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info(
        "application_started",
        extra={"environment": settings.environment},
    )
    yield
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Build the FastAPI application and wire transport-level concerns."""
    settings = get_settings()
    application = FastAPI(
        title="AerialOps API",
        version="0.1.0",
        description="Inspection and geospatial intelligence API",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
