"""FastAPI dependency wiring for ``llm-service``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pkg.internal_auth import InternalCaller, make_internal_caller_dep
from services.llm_service.app.clients.base import LlmAnalyzer
from services.llm_service.app.config import get_settings
from services.llm_service.app.services.analyzer import AnalyzerService


class LlmDeps:
    session_factory: async_sessionmaker[AsyncSession] | None = None
    analyzer: LlmAnalyzer | None = None


deps = LlmDeps()
_settings = get_settings()
_internal_caller = make_internal_caller_dep(_settings, "llm-service", "test-service")


async def get_session() -> AsyncIterator[AsyncSession]:
    assert deps.session_factory is not None
    async with deps.session_factory() as session:
        yield session


def get_analyzer_service(session: Annotated[AsyncSession, Depends(get_session)]) -> AnalyzerService:
    assert deps.analyzer is not None
    return AnalyzerService(session=session, analyzer=deps.analyzer)


InternalCallerDep = Annotated[InternalCaller, Depends(_internal_caller)]
