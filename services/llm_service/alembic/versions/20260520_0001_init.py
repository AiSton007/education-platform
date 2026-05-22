"""init llm schema

Revision ID: 0001_llm_init
Revises:
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001_llm_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "llm"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                           WHERE t.typname='analysis_status' AND n.nspname='{SCHEMA}') THEN
                CREATE TYPE {SCHEMA}.analysis_status AS ENUM ('pending','processing','completed','failed');
            END IF;
        END $$;
        """
    )

    op.create_table(
        "analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("attempt_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="analysis_status", schema=SCHEMA, create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("prompt", sa.Text, nullable=True),
        sa.Column("raw_response", JSONB, nullable=True),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("score", sa.Numeric(6, 2), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_llm_analyses_attempt_id", "analyses", ["attempt_id"], schema=SCHEMA)
    op.create_index("ix_llm_analyses_user_id", "analyses", ["user_id"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_llm_analyses_user_id", table_name="analyses", schema=SCHEMA)
    op.drop_index("ix_llm_analyses_attempt_id", table_name="analyses", schema=SCHEMA)
    op.drop_table("analyses", schema=SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.analysis_status")
