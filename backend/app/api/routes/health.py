from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app.db.session import database_is_ready

router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["aerialops-api"]
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Literal["ok", "unavailable"]]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return process liveness without querying downstream dependencies."""
    return HealthResponse(status="ok", service="aerialops-api", version="0.1.0")


@router.get("/ready", response_model=ReadinessResponse)
def readiness(
    response: Response,
    database_ready: Annotated[bool, Depends(database_is_ready)],
) -> ReadinessResponse:
    """Return whether required dependencies can serve application traffic."""
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="not_ready", checks={"database": "unavailable"})
    return ReadinessResponse(status="ready", checks={"database": "ok"})
