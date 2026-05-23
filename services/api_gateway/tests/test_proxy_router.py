"""Smoke test for ProxyRouter prefix matching."""

from __future__ import annotations

import pytest

from pkg.errors import NotFound
from services.api_gateway.app.proxy import ProxyRouter


def test_router_resolves_known_prefixes() -> None:
    router = ProxyRouter(
        auth_url="http://auth:8080",
        user_url="http://user:8080",
        test_url="http://test:8080",
        report_url="http://report:8080",
    )
    assert router.resolve("/api/v1/auth/login") == "http://auth:8080"
    assert router.resolve("/api/v1/users/me") == "http://user:8080"
    assert router.resolve("/api/v1/tests") == "http://test:8080"
    assert router.resolve("/api/v1/attempts/123/submit") == "http://test:8080"
    assert router.resolve("/api/v1/assignments") == "http://test:8080"
    assert router.resolve("/api/v1/assignments/me") == "http://test:8080"
    assert router.resolve("/api/v1/reports/abc") == "http://report:8080"


def test_router_rejects_unknown_path() -> None:
    router = ProxyRouter(auth_url="x", user_url="x", test_url="x", report_url="x")
    with pytest.raises(NotFound):
        router.resolve("/api/v1/unknown")
