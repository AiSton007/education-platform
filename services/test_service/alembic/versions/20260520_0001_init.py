"""init tests schema

Revision ID: 0001_tests_init
Revises:
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "0001_tests_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "tests"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                           WHERE t.typname='question_type' AND n.nspname='{SCHEMA}') THEN
                CREATE TYPE {SCHEMA}.question_type AS ENUM ('single','multiple','free_text');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                           WHERE t.typname='attempt_status' AND n.nspname='{SCHEMA}') THEN
                CREATE TYPE {SCHEMA}.attempt_status AS ENUM (
                    'started','submitted','analyzed','completed','failed'
                );
            END IF;
        END $$;
        """
    )

    op.create_table(
        "tests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_tests_created_by", "tests", ["created_by"], schema=SCHEMA)

    op.create_table(
        "questions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "single",
                "multiple",
                "free_text",
                name="question_type",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("weight", sa.Numeric(6, 2), nullable=False, server_default=sa.text("1.0")),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_questions_test_id", "questions", ["test_id"], schema=SCHEMA)

    op.create_table(
        "options",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "question_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("is_correct", sa.Boolean, nullable=False, server_default=sa.text("false")),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_options_question_id", "options", ["question_id"], schema=SCHEMA)

    op.create_table(
        "attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "started",
                "submitted",
                "analyzed",
                "completed",
                "failed",
                name="attempt_status",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="started",
        ),
        sa.Column("score", sa.Numeric(6, 2), nullable=True),
        sa.Column("report_id", UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_attempts_test_id", "attempts", ["test_id"], schema=SCHEMA)
    op.create_index("ix_tests_attempts_user_id", "attempts", ["user_id"], schema=SCHEMA)

    op.create_table(
        "answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "attempt_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_id", UUID(as_uuid=True), nullable=False),
        sa.Column("selected_option_ids", ARRAY(UUID(as_uuid=True)), nullable=True),
        sa.Column("free_text", sa.Text, nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_answers_attempt_id", "answers", ["attempt_id"], schema=SCHEMA)
    op.create_index("ix_tests_answers_question_id", "answers", ["question_id"], schema=SCHEMA)


def downgrade() -> None:
    for table in ("answers", "attempts", "options", "questions", "tests"):
        op.drop_table(table, schema=SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.attempt_status")
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.question_type")
