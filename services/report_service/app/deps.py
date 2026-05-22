"""FastAPI dependency wiring for ``report-service``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pkg.internal_auth import InternalCaller, make_internal_caller_dep
from pkg.jwt_auth import CurrentUser, make_current_user_dep
from services.report_service.app.config import get_settings
from services.report_service.app.services.reports import ReportsService


class ReportDeps:
    session_factory: async_sessionmaker[AsyncSession] | None = None


deps = ReportDeps()
_settings = get_settings()
_current_user = make_current_user_dep(_settings)
_internal_caller = make_internal_caller_dep(_settings, "report-service", "test-service")


async def get_session() -> AsyncIterator[AsyncSession]:
    assert deps.session_factory is not None
    async with deps.session_factory() as session:
        yield session


def get_reports_service(session: Annotated[AsyncSession, Depends(get_session)]) -> ReportsService:
    return ReportsService(session)


CurrentUserDep = Annotated[CurrentUser, Depends(_current_user)]
InternalCallerDep = Annotated[InternalCaller, Depends(_internal_caller)]
