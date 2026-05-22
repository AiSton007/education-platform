"""Application entrypoint for ``auth-service``."""

from __future__ import annotations

from fastapi import FastAPI

from pkg.app_factory import create_app
from pkg.db import build_engine, build_session_factory
from pkg.health import db_ready
from pkg.internal_auth import InternalIssuer
from services.auth_service.app.clients.user_service import UserServiceClient
from services.auth_service.app.config import get_settings
from services.auth_service.app.deps import deps
from services.auth_service.app.routes.auth import router as auth_router


def build_app() -> FastAPI:
    settings = get_settings()
    engine = build_engine(settings)
    deps.session_factory = build_session_factory(engine)
    deps.issuer = InternalIssuer(self_name=settings.app_name, settings=settings)
    deps.user_client = UserServiceClient(base_url=settings.user_service_url, issuer=deps.issuer)

    async def _on_shutdown(_: FastAPI) -> None:
        await engine.dispose()

    return create_app(
        settings=settings,
        service_name=settings.app_name,
        ready_checks=(db_ready(engine),),
        on_shutdown=_on_shutdown,
        routers=(auth_router,),
    )


app = build_app()
