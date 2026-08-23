import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.db.session import database_is_ready
from app.main import app


def request(path: str, headers: dict[str, str] | None = None) -> Response:
    async def send() -> Response:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send())


def test_health_reports_api_liveness() -> None:
    response = request("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "aerialops-api",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"]


def test_health_preserves_caller_request_id() -> None:
    response = request("/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"


def test_readiness_reports_available_database() -> None:
    app.dependency_overrides[database_is_ready] = lambda: True
    try:
        response = request("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": "ok"},
    }


def test_readiness_reports_unavailable_database() -> None:
    app.dependency_overrides[database_is_ready] = lambda: False
    try:
        response = request("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable"},
    }
