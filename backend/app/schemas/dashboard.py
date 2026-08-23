from pydantic import BaseModel, Field

from app.schemas.inspection import InspectionRead
from app.schemas.site import SiteRead


class DashboardMetrics(BaseModel):
    total_sites: int = Field(ge=0)
    active_sites: int = Field(ge=0)
    critical_sites: int = Field(ge=0)
    inspections_this_month: int = Field(ge=0)
    unresolved_anomalies: int = Field(ge=0)
    average_risk_score: float = Field(ge=0, le=100)


class DashboardSummary(BaseModel):
    metrics: DashboardMetrics
    recent_inspections: list[InspectionRead]
    highest_risk_sites: list[SiteRead]
    anomaly_counts_by_severity: dict[str, int]
