"""Free-form tests redesign (drop old shape, recreate).

Revision ID: 0002_tests_freeform
Revises: 0001_tests_init
Create Date: 2026-05-24 00:00:00

This migration performs an explicit drop & recreate of the test-service tables
to align them with the new free-form business model:
  * ``Option`` table removed completely
  * ``Question.correct_answer`` added (used by the LLM for grading)
  * ``Answer.selected_option_ids`` removed; ``Answer.score`` and ``Answer.feedback`` added
  * ``Attempt.score`` is now ``Numeric(3, 2)`` (0.0..1.0)
  * New ``assignments`` table and ``assignment_status`` enum
  * ``question_type`` enum is preserved (default ``free_text``) — UI/API only allow free_text now

Since the platform is still in its rollout phase, no data migration is performed.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002_tests_freeform"
down_revision: str | None = "0001_tests_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "tests"

question_type_enum = postgresql.ENUM(
    "single",
    "multiple",
    "free_text",
    name="question_type",
    schema=SCHEMA,
    create_type=False,
)
attempt_status_enum = postgresql.ENUM(
    "started",
    "submitted",
    "analyzed",
    "completed",
    "failed",
    name="attempt_status",
    schema=SCHEMA,
    create_type=False,
)
assignment_status_enum = postgresql.ENUM(
    "assigned",
    "in_progress",
    "completed",
    name="assignment_status",
    schema=SCHEMA,
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."answers" CASCADE')
    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."attempts" CASCADE')
    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."options" CASCADE')
    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."questions" CASCADE')
    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."assignments" CASCADE')
    op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."tests" CASCADE')

    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    question_type_enum.create(bind, checkfirst=True)
    attempt_status_enum.create(bind, checkfirst=True)
    assignment_status_enum.create(bind, checkfirst=True)

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
        sa.Column("type", question_type_enum, nullable=False, server_default="free_text"),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("correct_answer", sa.Text, nullable=False),
        sa.Column("weight", sa.Numeric(6, 2), nullable=False, server_default=sa.text("1.0")),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_questions_test_id", "questions", ["test_id"], schema=SCHEMA)

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
        sa.Column("status", attempt_status_enum, nullable=False, server_default="started"),
        sa.Column("score", sa.Numeric(3, 2), nullable=True),
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
        sa.Column("free_text", sa.Text, nullable=True),
        sa.Column("score", sa.Numeric(3, 2), nullable=True),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_answers_attempt_id", "answers", ["attempt_id"], schema=SCHEMA)
    op.create_index("ix_tests_answers_question_id", "answers", ["question_id"], schema=SCHEMA)

    op.create_table(
        "assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "test_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.tests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", UUID(as_uuid=True), nullable=False),
        sa.Column("status", assignment_status_enum, nullable=False, server_default="assigned"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("test_id", "user_id", name="uq_assignments_test_user"),
        schema=SCHEMA,
    )
    op.create_index("ix_tests_assignments_test_id", "assignments", ["test_id"], schema=SCHEMA)
    op.create_index("ix_tests_assignments_user_id", "assignments", ["user_id"], schema=SCHEMA)


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("assignments", "answers", "attempts", "questions", "tests"):
        op.execute(f'DROP TABLE IF EXISTS "{SCHEMA}"."{table}" CASCADE')
    assignment_status_enum.drop(bind, checkfirst=True)
    attempt_status_enum.drop(bind, checkfirst=True)
    question_type_enum.drop(bind, checkfirst=True)
