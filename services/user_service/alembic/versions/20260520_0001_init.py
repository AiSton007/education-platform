"""init users schema

Revision ID: 0001_users_init
Revises:
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_users_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "users"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE t.typname = 'user_role' AND n.nspname = '{SCHEMA}'
            ) THEN
                CREATE TYPE {SCHEMA}.user_role AS ENUM ('employee', 'manager', 'admin');
            END IF;
        END $$;
        """
    )

    op.create_table(
        "profiles",
        sa.Column("user_id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("position", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "employee",
                "manager",
                "admin",
                name="user_role",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="employee",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_users_profiles_email", "profiles", ["email"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_users_profiles_email", table_name="profiles", schema=SCHEMA)
    op.drop_table("profiles", schema=SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.user_role")
