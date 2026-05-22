"""Repo-wide pytest fixtures.

Tests that don't need a real database can rely on these fixtures to set the minimal
environment variables expected by ``pkg.config``.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _default_env() -> None:
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("LOG_LEVEL", "warning")
    os.environ.setdefault("METRICS_ENABLED", "false")

    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    os.environ.setdefault("JWT_ACCESS_TOKEN_TTL", "900")
    os.environ.setdefault("JWT_REFRESH_TOKEN_TTL", "604800")
    os.environ.setdefault("JWT_ISSUER", "education-platform")

    os.environ.setdefault("INTERNAL_JWT_SECRET", "test-internal-secret")
    os.environ.setdefault("INTERNAL_JWT_TTL", "300")

    os.environ.setdefault("DB_USER", "test")
    os.environ.setdefault("DB_PASSWORD", "test")
    os.environ.setdefault("DB_NAME", "test")
    os.environ.setdefault("DB_HOST", "localhost")
