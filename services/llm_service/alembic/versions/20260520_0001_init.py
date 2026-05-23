"""init llm schema

Revision ID: 0001_llm_init
Revises:
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_llm_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "llm"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.execute(
        f"""
        DO $$
        BEGIN
            CREATE TYPE "{SCHEMA}".analysis_status AS ENUM (
                'pending',
                'processing',
                'completed',
                'failed'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS "{SCHEMA}".analyses (
            id UUID PRIMARY KEY,
            attempt_id UUID NOT NULL,
            user_id UUID NOT NULL,
            status "{SCHEMA}".analysis_status NOT NULL DEFAULT 'pending'::"{SCHEMA}".analysis_status,
            prompt TEXT,
            raw_response JSONB,
            result JSONB,
            score NUMERIC(6, 2),
            error TEXT,
            provider TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(f'CREATE INDEX IF NOT EXISTS ix_llm_analyses_attempt_id ON "{SCHEMA}".analyses (attempt_id)')
    op.execute(f'CREATE INDEX IF NOT EXISTS ix_llm_analyses_user_id ON "{SCHEMA}".analyses (user_id)')


def downgrade() -> None:
    op.execute(f'DROP INDEX IF EXISTS "{SCHEMA}".ix_llm_analyses_user_id')
    op.execute(f'DROP INDEX IF EXISTS "{SCHEMA}".ix_llm_analyses_attempt_id')
    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}".analyses')
    op.execute(f'DROP TYPE IF EXISTS "{SCHEMA}".analysis_status')
