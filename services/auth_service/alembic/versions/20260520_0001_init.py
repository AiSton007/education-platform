"""init auth schema

Revision ID: 0001_auth_init
Revises:
Create Date: 2026-05-20 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_auth_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "auth"


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
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
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
    op.create_index("ix_auth_users_email", "users", ["email"], schema=SCHEMA)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("jti", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index("ix_auth_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema=SCHEMA)
    op.create_index("ix_auth_refresh_tokens_jti", "refresh_tokens", ["jti"], schema=SCHEMA, unique=True)


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_tokens_jti", table_name="refresh_tokens", schema=SCHEMA)
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="refresh_tokens", schema=SCHEMA)
    op.drop_table("refresh_tokens", schema=SCHEMA)

    op.drop_index("ix_auth_users_email", table_name="users", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)
    op.execute(f"DROP TYPE IF EXISTS {SCHEMA}.user_role")
