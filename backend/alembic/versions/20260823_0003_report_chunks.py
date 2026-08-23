"""Add persisted report chunks for local semantic retrieval.

Revision ID: 20260823_0003
Revises: 20260822_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260823_0003"
down_revision: str | None = "20260822_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_chunks",
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["inspection_reports.id"],
            name=op.f("fk_report_chunks_report_id_inspection_reports"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_chunks")),
        sa.UniqueConstraint("report_id", "chunk_index", name="uq_report_chunks_report_index"),
    )
    op.create_index("ix_report_chunks_report_id", "report_chunks", ["report_id"])


def downgrade() -> None:
    op.drop_table("report_chunks")
