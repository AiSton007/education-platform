"""Catch-all proxy route plus a lightweight JWT precheck."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from pkg.errors import Unauthorized
from pkg.jwt_auth import decode_token
from services.api_gateway.app.config import GatewaySettings, get_settings
from services.api_gateway.app.proxy import HttpProxy, ProxyRouter

router = APIRouter()

PUBLIC_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/healthz",
    "/readyz",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/openapi.yaml",
)


def _is_public(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES)


class GatewayState:
    proxy: HttpProxy | None = None
    router: ProxyRouter | None = None


state = GatewayState()


@router.api_route(
    "/api/v1/{full_path:path}",
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
)
async def proxy_all(
    full_path: str,
    request: Request,
    settings: Annotated[GatewaySettings, Depends(get_settings)],
) -> Response:
    assert state.proxy is not None and state.router is not None
    path = request.url.path

    if not _is_public(path):
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.lower().startswith("bearer "):
            raise Unauthorized("Missing bearer token")
        token = authorization.split(" ", 1)[1].strip()
        decode_token(settings, token, expected_type="access")

    upstream = state.router.resolve(path)
    return await state.proxy.forward(request, upstream)
