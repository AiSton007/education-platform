"""Unit tests for ``pkg.jwt_auth``."""

from __future__ import annotations

import pytest

from pkg.config import JWTSettings
from pkg.errors import Unauthorized
from pkg.jwt_auth import decode_token, issue_access_token, issue_refresh_token


@pytest.fixture
def jwt_settings() -> JWTSettings:
    return JWTSettings()


def test_issue_and_decode_access_token(jwt_settings: JWTSettings) -> None:
    token = issue_access_token(
        jwt_settings, user_id="11111111-1111-1111-1111-111111111111", role="admin", email="a@b.c"
    )
    decoded = decode_token(jwt_settings, token, expected_type="access")
    assert decoded["sub"] == "11111111-1111-1111-1111-111111111111"
    assert decoded["role"] == "admin"
    assert decoded["type"] == "access"


def test_decode_rejects_wrong_type(jwt_settings: JWTSettings) -> None:
    refresh, _ = issue_refresh_token(jwt_settings, user_id="x")
    with pytest.raises(Unauthorized):
        decode_token(jwt_settings, refresh, expected_type="access")


def test_decode_rejects_garbage(jwt_settings: JWTSettings) -> None:
    with pytest.raises(Unauthorized):
        decode_token(jwt_settings, "not-a-token", expected_type="access")
