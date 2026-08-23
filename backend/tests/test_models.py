from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Anomaly, ProcessingJob, Site
from app.models.enums import (
    AnomalyStatus,
    JobStatus,
    JobType,
    RiskLevel,
    SiteStatus,
    SiteType,
)
from app.schemas.site import SiteCreate
from scripts.seed_demo_data import seed_demo_data


def test_metadata_contains_requested_phase_two_tables() -> None:
    assert set(Base.metadata.tables) == {
        "agent_conversations",
        "agent_messages",
        "sites",
        "inspections",
        "inspection_images",
        "anomalies",
        "inspection_reports",
        "risk_assessments",
        "processing_jobs",
        "report_chunks",
    }


def test_seed_is_idempotent_and_meets_demo_minimums(db_session: Session) -> None:
    fixed_now = datetime(2026, 8, 22, 12, tzinfo=UTC)

    first_counts = seed_demo_data(db_session, now=fixed_now)
    second_counts = seed_demo_data(db_session, now=fixed_now)

    assert first_counts == second_counts
    assert second_counts == {
        "sites": 10,
        "inspections": 20,
        "inspection_images": 5,
        "anomalies": 28,
        "inspection_reports": 6,
        "risk_assessments": 10,
        "processing_jobs": 6,
        "report_chunks": 6,
    }


def test_seed_creates_relationships_and_multiple_risk_levels(db_session: Session) -> None:
    seed_demo_data(db_session, now=datetime(2026, 8, 22, 12, tzinfo=UTC))

    alpha = db_session.get(
        Site, next(site.id for site in db_session.query(Site) if site.name == "Solar Farm Alpha")
    )

    assert alpha is not None
    assert len(alpha.inspections) == 2
    assert len(alpha.anomalies) >= 3
    assert alpha.current_risk_level == RiskLevel.CRITICAL
    assert {site.current_risk_level for site in db_session.query(Site)} == {
        RiskLevel.LOW,
        RiskLevel.MODERATE,
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    }


def test_database_rejects_invalid_coordinates(db_session: Session) -> None:
    db_session.add(
        Site(
            name="Invalid coordinate site",
            site_type=SiteType.OTHER,
            location="Synthetic",
            latitude=Decimal("91.000000"),
            longitude=Decimal("10.000000"),
            status=SiteStatus.ACTIVE,
            current_risk_score=0,
            current_risk_level=RiskLevel.LOW,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_database_rejects_job_without_exactly_one_source(db_session: Session) -> None:
    db_session.add(
        ProcessingJob(
            job_type=JobType.REPORT_INGESTION,
            status=JobStatus.PENDING,
            report_id=None,
            image_id=None,
            attempts=0,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_pydantic_rejects_invalid_coordinates_before_database() -> None:
    with pytest.raises(ValueError):
        SiteCreate(
            name="Invalid coordinate site",
            site_type=SiteType.OTHER,
            location="Synthetic",
            latitude=Decimal("-91"),
            longitude=Decimal("10"),
        )


def test_database_enforces_resolved_anomaly_timestamp(sqlite_engine: Engine) -> None:
    with Session(sqlite_engine) as session:
        seed_demo_data(session, now=datetime(2026, 8, 22, 12, tzinfo=UTC))
        existing = session.query(Anomaly).first()
        assert existing is not None
        existing.status = AnomalyStatus.RESOLVED
        existing.resolved_at = None
        with pytest.raises(IntegrityError):
            session.commit()
