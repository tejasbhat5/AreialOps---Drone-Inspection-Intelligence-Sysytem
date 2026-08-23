from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.enums import (
    AnomalySeverity,
    AnomalyStatus,
    InspectionStatus,
    RiskLevel,
    SiteStatus,
    SiteType,
)
from app.models.inspection import Inspection
from app.models.site import Site
from app.services.risk_service import RiskService, classify_risk, recency_points


def test_risk_boundaries_and_recency_bands() -> None:
    assert [classify_risk(score) for score in (0, 30, 31, 60, 61, 80, 81, 100)] == [
        RiskLevel.LOW,
        RiskLevel.LOW,
        RiskLevel.MODERATE,
        RiskLevel.MODERATE,
        RiskLevel.HIGH,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
        RiskLevel.CRITICAL,
    ]
    assert [recency_points(days) for days in (0, 30, 31, 60, 61, 90, 91, None)] == [
        0,
        0,
        3,
        3,
        6,
        6,
        10,
        10,
    ]


def test_risk_calculation_is_reproducible_and_capped(db_session: Session) -> None:
    now = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)
    site = Site(
        name="Risk Formula Site",
        site_type=SiteType.SOLAR_FARM,
        location="Synthetic",
        latitude=26.9,
        longitude=70.9,
        status=SiteStatus.ACTIVE,
        current_risk_score=0,
        current_risk_level=RiskLevel.LOW,
    )
    db_session.add(site)
    db_session.flush()
    inspection = Inspection(
        site_id=site.id,
        inspected_at=now - timedelta(days=65),
        status=InspectionStatus.COMPLETED,
    )
    db_session.add(inspection)
    db_session.flush()
    for index in range(4):
        db_session.add(
            Anomaly(
                site_id=site.id,
                inspection_id=inspection.id,
                title=f"Critical {index}",
                description="Synthetic critical finding.",
                severity=AnomalySeverity.CRITICAL,
                status=AnomalyStatus.OPEN,
            )
        )
    db_session.flush()

    calculation = RiskService(db_session).calculate(site.id, now=now)

    assert calculation.score == 93
    assert calculation.level == RiskLevel.CRITICAL
    assert calculation.factors["severity_raw_points"] == 80
    assert calculation.factors["severity_points"] == 60
    assert calculation.factors["critical_bonus"] == 15
    assert calculation.factors["volume_points"] == 12
    assert calculation.factors["recency_points"] == 6
