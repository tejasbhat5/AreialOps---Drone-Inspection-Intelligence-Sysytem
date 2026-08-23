from fastapi import APIRouter

from app.api.routes import (
    anomalies,
    assistant,
    dashboard,
    health,
    inspections,
    jobs,
    reports,
    sites,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(sites.router, tags=["sites"])
api_router.include_router(inspections.router, tags=["inspections"])
api_router.include_router(anomalies.router, tags=["anomalies"])
api_router.include_router(assistant.router, tags=["assistant"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(jobs.router, tags=["jobs"])
