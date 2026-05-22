"""HTTP client helpers for service-to-service calls.

Wraps :class:`httpx.AsyncClient` with:
- automatic injection of an internal JWT (``X-Internal-Token``) for the configured audience,
- propagation of ``X-Request-Id``,
- propagation of the caller's ``Authorization`` (user JWT) when available,
- sane default timeouts.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx

from pkg.errors import UpstreamError
from pkg.internal_auth import INTERNAL_TOKEN_HEADER, InternalIssuer
from pkg.logger import get_request_id

DEFAULT_TIMEOUT = httpx.Timeout(connect=2.0, read=15.0, write=15.0, pool=2.0)


class InternalClient:
    """Async HTTP client preconfigured for talking to a single peer service."""

    def __init__(
        self,
        *,
        base_url: str,
        audience: str,
        issuer: InternalIssuer,
        timeout: httpx.Timeout | float | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._audience = audience
        self._issuer = issuer
        self._timeout = timeout or DEFAULT_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> InternalClient:
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _headers(self, *, user_jwt: str | None = None) -> dict[str, str]:
        h: dict[str, str] = {INTERNAL_TOKEN_HEADER: self._issuer.token(self._audience)}
        rid = get_request_id()
        if rid:
            h["X-Request-Id"] = rid
        if user_jwt:
            h["Authorization"] = user_jwt
        return h

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict | None = None,
        user_jwt: str | None = None,
    ) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("InternalClient must be used inside `async with`")
        try:
            response = await self._client.request(
                method,
                path,
                json=json,
                params=params,
                headers=self._headers(user_jwt=user_jwt),
            )
        except httpx.RequestError as exc:
            raise UpstreamError(
                message=f"Upstream call failed: {exc.__class__.__name__}",
                details={"target": self._audience, "url": str(exc.request.url) if exc.request else None},
            ) from exc
        if response.status_code >= 500:
            raise UpstreamError(
                message=f"Upstream {self._audience} returned {response.status_code}",
                details={
                    "target": self._audience,
                    "status": response.status_code,
                    "body": response.text[:500],
                },
            )
        return response

    async def get(self, path: str, **kw: Any) -> httpx.Response:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> httpx.Response:
        return await self.request("POST", path, **kw)

    async def patch(self, path: str, **kw: Any) -> httpx.Response:
        return await self.request("PATCH", path, **kw)

    async def delete(self, path: str, **kw: Any) -> httpx.Response:
        return await self.request("DELETE", path, **kw)


@asynccontextmanager
async def internal_client(
    base_url: str,
    audience: str,
    issuer: InternalIssuer,
    request_timeout: httpx.Timeout | float | None = None,
):
    """Convenience async context manager wrapping :class:`InternalClient`."""
    async with InternalClient(
        base_url=base_url, audience=audience, issuer=issuer, timeout=request_timeout
    ) as client:
        yield client
