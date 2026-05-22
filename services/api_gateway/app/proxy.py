"""Reverse-proxy core for api-gateway.

A single ``httpx.AsyncClient`` is shared across all upstreams; the request is forwarded
verbatim (method, body, headers minus hop-by-hop). ``Authorization`` is preserved so the user
JWT reaches the backend service that owns the resource.
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import Request
from fastapi.responses import Response

from pkg.errors import NotFound, UpstreamError
from pkg.logger import get_request_id

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


class ProxyRouter:
    """Selects an upstream URL based on the incoming path prefix."""

    def __init__(
        self,
        *,
        auth_url: str,
        user_url: str,
        test_url: str,
        report_url: str,
    ) -> None:
        self._rules: tuple[tuple[str, str], ...] = (
            ("/api/v1/auth", auth_url),
            ("/api/v1/users", user_url),
            ("/api/v1/tests", test_url),
            ("/api/v1/attempts", test_url),
            ("/api/v1/reports", report_url),
        )

    def resolve(self, path: str) -> str:
        for prefix, upstream in self._rules:
            if path == prefix or path.startswith(prefix + "/"):
                return upstream
        raise NotFound(f"No upstream for path {path}")


class HttpProxy:
    def __init__(self, *, timeout_seconds: float) -> None:
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def forward(self, request: Request, upstream_base: str) -> Response:
        url = upstream_base.rstrip("/") + request.url.path
        if request.url.query:
            url = f"{url}?{request.url.query}"

        headers = {
            k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP
        }
        rid = get_request_id()
        if rid:
            headers["X-Request-Id"] = rid
        headers["Host"] = urlparse(upstream_base).netloc

        body = await request.body()
        try:
            upstream = await self._client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                follow_redirects=False,
            )
        except httpx.RequestError as exc:
            raise UpstreamError(
                f"Proxy failed: {exc.__class__.__name__}",
                details={"upstream": upstream_base, "path": request.url.path},
            ) from exc

        response_headers = {
            k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP
        }
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type"),
        )
