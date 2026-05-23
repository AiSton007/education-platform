"""FastAPI dependency wiring for ``test-service``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pkg.internal_auth import InternalIssuer
from pkg.jwt_auth import CurrentUser, make_current_user_dep
from services.test_service.app.clients.llm_service import LlmServiceClient
from services.test_service.app.clients.report_service import ReportServiceClient
from services.test_service.app.clients.user_service import UserServiceClient
from services.test_service.app.config import get_settings
from services.test_service.app.services.assignments import AssignmentsService
from services.test_service.app.services.attempts import AttemptsService
from services.test_service.app.services.tests import TestsService


class TestDeps:
    session_factory: async_sessionmaker[AsyncSession] | None = None
    issuer: InternalIssuer | None = None
    llm_client: LlmServiceClient | None = None
    report_client: ReportServiceClient | None = None
    user_client: UserServiceClient | None = None


deps = TestDeps()

_settings = get_settings()
_current_user_resolver = make_current_user_dep(_settings)


async def get_session() -> AsyncIterator[AsyncSession]:
    assert deps.session_factory is not None
    async with deps.session_factory() as session:
        yield session


def get_tests_service(session: Annotated[AsyncSession, Depends(get_session)]) -> TestsService:
    return TestsService(session)


def get_attempts_service(session: Annotated[AsyncSession, Depends(get_session)]) -> AttemptsService:
    assert (
        deps.llm_client is not None
        and deps.report_client is not None
        and deps.user_client is not None
    )
    return AttemptsService(
        session=session,
        llm_client=deps.llm_client,
        report_client=deps.report_client,
        user_client=deps.user_client,
    )


def get_assignments_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AssignmentsService:
    return AssignmentsService(session)


CurrentUserDep = Annotated[CurrentUser, Depends(_current_user_resolver)]
