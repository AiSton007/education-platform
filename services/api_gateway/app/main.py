"""Application entrypoint for ``api-gateway``."""

from __future__ import annotations

from fastapi import FastAPI

from pkg.app_factory import create_app
from services.api_gateway.app.config import get_settings
from services.api_gateway.app.proxy import HttpProxy, ProxyRouter
from services.api_gateway.app.routes import router as proxy_router
from services.api_gateway.app.routes import state


def build_app() -> FastAPI:
    settings = get_settings()
    state.proxy = HttpProxy(timeout_seconds=settings.proxy_timeout_seconds)
    state.router = ProxyRouter(
        auth_url=settings.auth_service_url,
        user_url=settings.user_service_url,
        test_url=settings.test_service_url,
        report_url=settings.report_service_url,
    )

    async def _on_shutdown(_: FastAPI) -> None:
        if state.proxy is not None:
            await state.proxy.aclose()

    return create_app(
        settings=settings,
        service_name=settings.app_name,
        on_shutdown=_on_shutdown,
        routers=(proxy_router,),
    )


app = build_app()
