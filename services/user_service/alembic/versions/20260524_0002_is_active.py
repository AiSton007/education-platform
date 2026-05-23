"""Add is_active flag to user profiles.

Revision ID: 0002_users_is_active
Revises: 0001_users_init
Create Date: 2026-05-24 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_users_is_active"
down_revision: str | None = "0001_users_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "users"


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("profiles", "is_active", schema=SCHEMA)
