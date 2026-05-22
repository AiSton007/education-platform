"""Application entrypoint for ``user-service``."""

from __future__ import annotations

from fastapi import FastAPI

from pkg.app_factory import create_app
from pkg.db import build_engine, build_session_factory
from pkg.health import db_ready
from services.user_service.app.config import get_settings
from services.user_service.app.deps import deps
from services.user_service.app.routes.users import router as users_router


def build_app() -> FastAPI:
    settings = get_settings()
    engine = build_engine(settings)
    deps.session_factory = build_session_factory(engine)

    async def _on_shutdown(_: FastAPI) -> None:
        await engine.dispose()

    return create_app(
        settings=settings,
        service_name=settings.app_name,
        ready_checks=(db_ready(engine),),
        on_shutdown=_on_shutdown,
        routers=(users_router,),
    )


app = build_app()
