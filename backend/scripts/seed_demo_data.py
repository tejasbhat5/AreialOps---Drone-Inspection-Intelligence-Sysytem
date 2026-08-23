from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory
from app.models import (
    Anomaly,
    Inspection,
    InspectionImage,
    InspectionReport,
    ProcessingJob,
    ReportChunk,
    RiskAssessment,
    Site,
)
from app.models.enums import (
    AnomalySeverity,
    AnomalyStatus,
    ImageReviewStatus,
    InspectionStatus,
    JobStatus,
    JobType,
    ReportIngestionStatus,
    RiskLevel,
    SiteStatus,
    SiteType,
)
from app.rag.embedding_service import LocalHashEmbeddingService

SEED_NAMESPACE = UUID("5955fc88-7714-4bc5-bd4c-05f46f5f4714")


@dataclass(frozen=True)
class SiteSeed:
    name: str
    site_type: SiteType
    location: str
    latitude: str
    longitude: str
    risk_score: int


SITES = (
    SiteSeed(
        "Solar Farm Alpha",
        SiteType.SOLAR_FARM,
        "Jaisalmer, Rajasthan",
        "26.915700",
        "70.908300",
        92,
    ),
    SiteSeed("Wind Farm Delta", SiteType.WIND_FARM, "Kutch, Gujarat", "23.733700", "69.859700", 78),
    SiteSeed(
        "Rail Corridor 14", SiteType.RAIL, "Nagpur, Maharashtra", "21.145800", "79.088200", 85
    ),
    SiteSeed("Highway Bridge B7", SiteType.BRIDGE, "Kochi, Kerala", "9.931200", "76.267300", 64),
    SiteSeed("Mining Zone Echo", SiteType.MINE, "Ballari, Karnataka", "15.139400", "76.921400", 55),
    SiteSeed(
        "Transmission Cluster 8",
        SiteType.TRANSMISSION,
        "Indore, Madhya Pradesh",
        "22.719600",
        "75.857700",
        48,
    ),
    SiteSeed(
        "Industrial Plant North",
        SiteType.INDUSTRIAL,
        "Pune, Maharashtra",
        "18.520400",
        "73.856700",
        37,
    ),
    SiteSeed(
        "Construction Zone Vega",
        SiteType.CONSTRUCTION,
        "Hyderabad, Telangana",
        "17.385000",
        "78.486700",
        28,
    ),
    SiteSeed(
        "Solar Field Orion", SiteType.SOLAR_FARM, "Bikaner, Rajasthan", "28.022900", "73.311900", 18
    ),
    SiteSeed("Rail Section 22", SiteType.RAIL, "Bhubaneswar, Odisha", "20.296100", "85.824500", 8),
)


def stable_id(value: str) -> UUID:
    return uuid5(SEED_NAMESPACE, value)


def risk_level(score: int) -> RiskLevel:
    if score <= 30:
        return RiskLevel.LOW
    if score <= 60:
        return RiskLevel.MODERATE
    if score <= 80:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


def severity_for(score: int, offset: int) -> AnomalySeverity:
    if score >= 81 and offset == 0:
        return AnomalySeverity.CRITICAL
    if score >= 61:
        return AnomalySeverity.HIGH
    if score >= 31:
        return AnomalySeverity.MODERATE
    return AnomalySeverity.LOW


def seed_demo_data(session: Session, *, now: datetime | None = None) -> dict[str, int]:
    """Insert stable synthetic demo records without duplicating existing seed IDs."""
    current_time = now or datetime.now(UTC)

    for site_index, item in enumerate(SITES):
        site_id = stable_id(f"site:{item.name}")
        level = risk_level(item.risk_score)
        if session.get(Site, site_id) is None:
            session.add(
                Site(
                    id=site_id,
                    name=item.name,
                    site_type=item.site_type,
                    location=item.location,
                    latitude=Decimal(item.latitude),
                    longitude=Decimal(item.longitude),
                    status=SiteStatus.ACTIVE,
                    current_risk_score=item.risk_score,
                    current_risk_level=level,
                )
            )
            session.flush()

        assessment_id = stable_id(f"risk:{item.name}:seed-v1")
        if session.get(RiskAssessment, assessment_id) is None:
            session.add(
                RiskAssessment(
                    id=assessment_id,
                    site_id=site_id,
                    score=item.risk_score,
                    level=level,
                    formula_version="seed-v1",
                    factor_snapshot={
                        "source": "synthetic_demo_data",
                        "severity_points": min(item.risk_score, 60),
                        "critical_bonus": 15 if item.risk_score >= 81 else 0,
                        "volume_points": max(0, min(15, item.risk_score - 60)),
                        "recency_points": 10 if site_index < 3 else 3,
                    },
                    calculated_at=current_time - timedelta(days=site_index),
                )
            )

        for inspection_index in range(2):
            inspection_id = stable_id(f"inspection:{item.name}:{inspection_index}")
            inspected_at = current_time - timedelta(
                days=14 + site_index * 2 + inspection_index * 62
            )
            if session.get(Inspection, inspection_id) is None:
                session.add(
                    Inspection(
                        id=inspection_id,
                        site_id=site_id,
                        inspected_at=inspected_at,
                        status=InspectionStatus.COMPLETED,
                        notes=(
                            f"Synthetic {'recent' if inspection_index == 0 else 'previous'} "
                            f"inspection for {item.name}."
                        ),
                    )
                )
                session.flush()

            anomaly_count = 2 if site_index < 8 and inspection_index == 0 else 1
            for anomaly_index in range(anomaly_count):
                anomaly_id = stable_id(f"anomaly:{item.name}:{inspection_index}:{anomaly_index}")
                if session.get(Anomaly, anomaly_id) is not None:
                    continue
                resolved = inspection_index == 1 and (site_index + anomaly_index) % 2 == 0
                anomaly_status_value = AnomalyStatus.RESOLVED if resolved else AnomalyStatus.OPEN
                session.add(
                    Anomaly(
                        id=anomaly_id,
                        site_id=site_id,
                        inspection_id=inspection_id,
                        title=(
                            "Thermal hotspot"
                            if item.site_type == SiteType.SOLAR_FARM
                            else "Surface condition finding"
                        ),
                        description=(
                            f"Synthetic finding {anomaly_index + 1} recorded during the "
                            f"inspection of {item.name}."
                        ),
                        severity=severity_for(item.risk_score, anomaly_index),
                        status=anomaly_status_value,
                        resolved_at=inspected_at + timedelta(days=5) if resolved else None,
                    )
                )

            if inspection_index == 1 and site_index < 6:
                report_id = stable_id(f"report:{item.name}:{inspection_index}")
                primary_severity = severity_for(item.risk_score, 0).value.lower()
                report_text = (
                    f"Previous inspection report for {item.name}. "
                    "The team recorded a "
                    f"{primary_severity} condition finding, "
                    "verified access routes, and recommended follow-up during the next "
                    "scheduled inspection. This is synthetic demo content."
                )
                if session.get(InspectionReport, report_id) is None:
                    session.add(
                        InspectionReport(
                            id=report_id,
                            inspection_id=inspection_id,
                            storage_key=f"demo/reports/{report_id}.txt",
                            original_filename=f"{item.name.lower().replace(' ', '-')}-previous.txt",
                            content_type="text/plain",
                            size_bytes=512 + site_index * 41,
                            ingestion_status=ReportIngestionStatus.COMPLETED,
                            extracted_text=report_text,
                        )
                    )
                    session.flush()

                chunk_id = stable_id(f"report-chunk:{item.name}:{inspection_index}:0")
                if session.get(ReportChunk, chunk_id) is None:
                    session.add(
                        ReportChunk(
                            id=chunk_id,
                            report_id=report_id,
                            chunk_index=0,
                            content=report_text,
                            token_count=len(report_text.split()),
                            embedding=LocalHashEmbeddingService().embed(report_text),
                        )
                    )

                job_id = stable_id(f"job:report:{item.name}:{inspection_index}")
                if session.get(ProcessingJob, job_id) is None:
                    session.add(
                        ProcessingJob(
                            id=job_id,
                            job_type=JobType.REPORT_INGESTION,
                            status=JobStatus.COMPLETED,
                            report_id=report_id,
                            image_id=None,
                            attempts=1,
                            started_at=inspected_at + timedelta(minutes=2),
                            completed_at=inspected_at + timedelta(minutes=3),
                        )
                    )

            if inspection_index == 0 and site_index < 5:
                image_id = stable_id(f"image:{item.name}:{inspection_index}")
                if session.get(InspectionImage, image_id) is None:
                    session.add(
                        InspectionImage(
                            id=image_id,
                            inspection_id=inspection_id,
                            storage_key=f"demo/images/{image_id}.jpg",
                            original_filename=f"{item.name.lower().replace(' ', '-')}-overview.jpg",
                            content_type="image/jpeg",
                            size_bytes=204_800 + site_index * 10_000,
                            review_status=ImageReviewStatus.NOT_ANALYZED,
                            ai_findings=None,
                        )
                    )

    session.commit()
    model_types = (
        Site,
        Inspection,
        InspectionImage,
        Anomaly,
        InspectionReport,
        RiskAssessment,
        ProcessingJob,
        ReportChunk,
    )
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
        for model in model_types
    }


def main() -> None:
    with get_session_factory()() as session:
        counts = seed_demo_data(session)
    print("AerialOps demo data ready:")
    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
