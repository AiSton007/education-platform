"""Factory that wires together every cross-cutting concern of a service.

Each service's ``main.py`` should simply call :func:`create_app` to obtain a fully configured
``FastAPI`` instance.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Iterable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from pkg.config import BaseAppSettings
from pkg.errors import register_exception_handlers
from pkg.health import ReadyCheck
from pkg.logger import bind_request_id, get_logger, setup_logging
from pkg.metrics import instrument

REQUEST_ID_HEADER = "X-Request-Id"

Lifespan = Callable[[FastAPI], Awaitable[None]]


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        bind_request_id(rid)
        structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            response: Response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
            bind_request_id(None)
        response.headers[REQUEST_ID_HEADER] = rid
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: structlog.stdlib.BoundLogger) -> None:
        super().__init__(app)
        self._log = logger

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        if request.url.path in {"/healthz", "/readyz", "/metrics"}:
            return response
        self._log.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            client=request.client.host if request.client else None,
        )
        return response


def create_app(
    *,
    settings: BaseAppSettings,
    service_name: str,
    ready_checks: Iterable[ReadyCheck] = (),
    on_startup: Lifespan | None = None,
    on_shutdown: Lifespan | None = None,
    routers: Iterable[object] = (),
    cors_origins: list[str] | None = None,
    docs_url: str | None = "/docs",
    redoc_url: str | None = "/redoc",
    openapi_url: str | None = "/openapi.json",
) -> FastAPI:
    """Build a fully configured FastAPI application.

    Adds: structured logging, request-id middleware, access logging, CORS, metrics,
    unified error handling, ``/healthz``, ``/readyz``, ``/openapi.yaml``.
    """
    setup_logging(settings.log_level, service_name)
    log = get_logger(service_name)

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        log.info("service_starting", env=settings.app_env, port=settings.app_port)
        if on_startup is not None:
            await on_startup(app)
        yield
        log.info("service_stopping")
        if on_shutdown is not None:
            await on_shutdown(app)
        log.info("service_stopped")

    app = FastAPI(
        title=service_name,
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=_lifespan,
    )

    # ---------- middlewares ----------
    origins = cors_origins or [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(AccessLogMiddleware, logger=log)
    app.add_middleware(RequestIdMiddleware)

    # ---------- error handlers ----------
    register_exception_handlers(app)

    # ---------- routers ----------
    for router in routers:
        app.include_router(router)

    # ---------- healthz / readyz ----------
    checks = list(ready_checks)

    @app.get("/healthz", include_in_schema=False)
    async def _healthz() -> PlainTextResponse:
        return PlainTextResponse("ok")

    @app.get("/readyz", include_in_schema=False)
    async def _readyz():
        failures: list[str] = []
        for check in checks:
            try:
                await check()
            except Exception as exc:
                failures.append(str(exc))
        if failures:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "failures": failures},
            )
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})

    # ---------- OpenAPI YAML ----------
    @app.get("/openapi.yaml", include_in_schema=False)
    async def _openapi_yaml():
        import yaml  # imported lazily — only needed if explicitly requested

        return PlainTextResponse(
            yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True),
            media_type="application/yaml",
        )

    # ---------- metrics ----------
    if settings.metrics_enabled:
        instrument(app, service_name)

    return app
