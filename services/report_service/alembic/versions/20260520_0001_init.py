"""init reports schema

Revision ID: 0001_reports_init
Revises:
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001_reports_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "reports"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("attempt_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Numeric(6, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("data", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_reports_reports_attempt_id", "reports", ["attempt_id"], schema=SCHEMA)
    op.create_index("ix_reports_reports_user_id", "reports", ["user_id"], schema=SCHEMA)

    op.create_table(
        "recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("resource_url", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_reports_recommendations_report_id", "recommendations", ["report_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_reports_recommendations_report_id", table_name="recommendations", schema=SCHEMA)
    op.drop_table("recommendations", schema=SCHEMA)
    op.drop_index("ix_reports_reports_user_id", table_name="reports", schema=SCHEMA)
    op.drop_index("ix_reports_reports_attempt_id", table_name="reports", schema=SCHEMA)
    op.drop_table("reports", schema=SCHEMA)
