"""Unit tests for ``pkg.internal_auth``."""

from __future__ import annotations

import asyncio

import jwt
import pytest

from pkg.config import InternalJWTSettings
from pkg.errors import Forbidden, Unauthorized
from pkg.internal_auth import InternalIssuer, make_internal_caller_dep


@pytest.fixture
def settings() -> InternalJWTSettings:
    return InternalJWTSettings()


def test_issuer_creates_token_with_audience(settings: InternalJWTSettings) -> None:
    issuer = InternalIssuer("test-service", settings)
    token = issuer.token("llm-service")
    payload = jwt.decode(
        token,
        settings.internal_jwt_secret,
        algorithms=[settings.internal_jwt_algorithm],
        audience="llm-service",
    )
    assert payload["iss"] == "test-service"
    assert payload["aud"] == "llm-service"


def test_caller_dep_accepts_allowed_issuer(settings: InternalJWTSettings) -> None:
    issuer = InternalIssuer("test-service", settings)
    dep = make_internal_caller_dep(settings, "llm-service", "test-service")
    caller = asyncio.run(dep(token=issuer.token("llm-service")))
    assert caller.issuer == "test-service"


def test_caller_dep_rejects_unknown_issuer(settings: InternalJWTSettings) -> None:
    issuer = InternalIssuer("auth-service", settings)
    dep = make_internal_caller_dep(settings, "llm-service", "test-service")
    with pytest.raises(Forbidden):
        asyncio.run(dep(token=issuer.token("llm-service")))


def test_caller_dep_rejects_missing_token(settings: InternalJWTSettings) -> None:
    dep = make_internal_caller_dep(settings, "llm-service", "test-service")
    with pytest.raises(Unauthorized):
        asyncio.run(dep(token=None))


def test_caller_dep_rejects_wrong_audience(settings: InternalJWTSettings) -> None:
    issuer = InternalIssuer("test-service", settings)
    dep = make_internal_caller_dep(settings, "report-service", "test-service")
    with pytest.raises((Unauthorized, Forbidden)):
        asyncio.run(dep(token=issuer.token("llm-service")))
