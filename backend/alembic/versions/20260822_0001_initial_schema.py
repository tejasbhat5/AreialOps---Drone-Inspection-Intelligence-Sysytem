"""Create the initial AerialOps operational schema.

Revision ID: 20260822_0001
Revises: None
Create Date: 2026-08-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260822_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

site_type = sa.Enum(
    "SOLAR_FARM",
    "WIND_FARM",
    "RAIL",
    "BRIDGE",
    "MINE",
    "TRANSMISSION",
    "INDUSTRIAL",
    "CONSTRUCTION",
    "OTHER",
    name="site_type",
)
site_status = sa.Enum("ACTIVE", "INACTIVE", "MAINTENANCE", "ARCHIVED", name="site_status")
risk_level = sa.Enum("LOW", "MODERATE", "HIGH", "CRITICAL", name="risk_level")
inspection_status = sa.Enum(
    "SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="inspection_status"
)
image_review_status = sa.Enum(
    "NOT_ANALYZED", "PENDING_REVIEW", "APPROVED", "REJECTED", name="image_review_status"
)
anomaly_severity = sa.Enum("LOW", "MODERATE", "HIGH", "CRITICAL", name="anomaly_severity")
anomaly_status = sa.Enum(
    "OPEN", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE", name="anomaly_status"
)
report_ingestion_status = sa.Enum(
    "NOT_STARTED", "PENDING", "PROCESSING", "COMPLETED", "FAILED", name="report_ingestion_status"
)
job_type = sa.Enum("REPORT_INGESTION", "IMAGE_ANALYSIS", name="job_type")
job_status = sa.Enum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="job_status")


def timestamp_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("site_type", site_type, nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("status", site_status, nullable=False),
        sa.Column("current_risk_score", sa.Integer(), nullable=False),
        sa.Column("current_risk_level", risk_level, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "current_risk_score >= 0 AND current_risk_score <= 100",
            name=op.f("ck_sites_current_risk_score_range"),
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90", name=op.f("ck_sites_latitude_range")
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180", name=op.f("ck_sites_longitude_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sites")),
    )
    op.create_index("ix_sites_coordinates", "sites", ["latitude", "longitude"])
    op.create_index("ix_sites_site_type", "sites", ["site_type"])
    op.create_index("ix_sites_status_risk", "sites", ["status", "current_risk_level"])
    op.create_index("uq_sites_name_lower", "sites", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "inspections",
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", inspection_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_inspections_site_id_sites"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inspections")),
    )
    op.create_index("ix_inspections_site_inspected_at", "inspections", ["site_id", "inspected_at"])
    op.create_index("ix_inspections_status_inspected_at", "inspections", ["status", "inspected_at"])

    op.create_table(
        "inspection_images",
        sa.Column("inspection_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("review_status", image_review_status, nullable=False),
        sa.Column("ai_findings", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_inspection_images_positive_size")),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            ["inspections.id"],
            name=op.f("fk_inspection_images_inspection_id_inspections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inspection_images")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_inspection_images_storage_key")),
    )
    op.create_index(
        op.f("ix_inspection_images_inspection_id"), "inspection_images", ["inspection_id"]
    )

    op.create_table(
        "inspection_reports",
        sa.Column("inspection_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("ingestion_status", report_ingestion_status, nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_inspection_reports_positive_size")),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            ["inspections.id"],
            name=op.f("fk_inspection_reports_inspection_id_inspections"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inspection_reports")),
        sa.UniqueConstraint("inspection_id", name=op.f("uq_inspection_reports_inspection_id")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_inspection_reports_storage_key")),
    )

    op.create_table(
        "anomalies",
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("inspection_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", anomaly_severity, nullable=False),
        sa.Column("status", anomaly_status, nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "(status = 'RESOLVED' AND resolved_at IS NOT NULL) OR "
            "(status <> 'RESOLVED' AND resolved_at IS NULL)",
            name=op.f("ck_anomalies_resolved_at_matches_status"),
        ),
        sa.ForeignKeyConstraint(
            ["inspection_id"],
            ["inspections.id"],
            name=op.f("fk_anomalies_inspection_id_inspections"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name=op.f("fk_anomalies_site_id_sites"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anomalies")),
    )
    op.create_index(op.f("ix_anomalies_inspection_id"), "anomalies", ["inspection_id"])
    op.create_index(
        "ix_anomalies_site_status_severity", "anomalies", ["site_id", "status", "severity"]
    )
    op.create_index("ix_anomalies_status_created_at", "anomalies", ["status", "created_at"])

    op.create_table(
        "risk_assessments",
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("level", risk_level, nullable=False),
        sa.Column("formula_version", sa.String(length=50), nullable=False),
        sa.Column("factor_snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100", name=op.f("ck_risk_assessments_score_range")
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name=op.f("fk_risk_assessments_site_id_sites"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_assessments")),
    )
    op.create_index(
        "ix_risk_assessments_site_calculated",
        "risk_assessments",
        ["site_id", "calculated_at"],
    )

    op.create_table(
        "processing_jobs",
        sa.Column("job_type", job_type, nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("image_id", sa.Uuid(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_processing_jobs_attempts_non_negative")),
        sa.CheckConstraint(
            "(report_id IS NOT NULL AND image_id IS NULL) OR "
            "(report_id IS NULL AND image_id IS NOT NULL)",
            name=op.f("ck_processing_jobs_exactly_one_source"),
        ),
        sa.ForeignKeyConstraint(
            ["image_id"],
            ["inspection_images.id"],
            name=op.f("fk_processing_jobs_image_id_inspection_images"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["inspection_reports.id"],
            name=op.f("fk_processing_jobs_report_id_inspection_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_processing_jobs")),
    )
    op.create_index(op.f("ix_processing_jobs_image_id"), "processing_jobs", ["image_id"])
    op.create_index(op.f("ix_processing_jobs_report_id"), "processing_jobs", ["report_id"])
    op.create_index(
        "ix_processing_jobs_status_created", "processing_jobs", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("processing_jobs")
    op.drop_table("risk_assessments")
    op.drop_table("anomalies")
    op.drop_table("inspection_reports")
    op.drop_table("inspection_images")
    op.drop_table("inspections")
    op.drop_table("sites")
