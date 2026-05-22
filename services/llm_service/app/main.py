"""Application entrypoint for ``llm-service``."""

from __future__ import annotations

from fastapi import FastAPI

from pkg.app_factory import create_app
from pkg.db import build_engine, build_session_factory
from pkg.health import db_ready
from services.llm_service.app.clients.base import LlmAnalyzer
from services.llm_service.app.clients.gigachat import GigaChatAnalyzer
from services.llm_service.app.clients.mock import MockAnalyzer
from services.llm_service.app.config import get_settings
from services.llm_service.app.deps import deps
from services.llm_service.app.routes.analyze import router as analyze_router


def _build_analyzer(settings) -> LlmAnalyzer:
    provider = (settings.llm_provider or "mock").lower()
    if provider == "gigachat":
        return GigaChatAnalyzer(settings)
    if provider == "mock":
        return MockAnalyzer()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def build_app() -> FastAPI:
    settings = get_settings()
    engine = build_engine(settings)
    deps.session_factory = build_session_factory(engine)
    deps.analyzer = _build_analyzer(settings)

    async def _on_shutdown(_: FastAPI) -> None:
        if hasattr(deps.analyzer, "aclose"):
            await deps.analyzer.aclose()  # type: ignore[attr-defined]
        await engine.dispose()

    return create_app(
        settings=settings,
        service_name=settings.app_name,
        ready_checks=(db_ready(engine),),
        on_shutdown=_on_shutdown,
        routers=(analyze_router,),
    )


app = build_app()
