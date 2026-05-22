"""FastAPI dependency wiring for ``user-service``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pkg.internal_auth import InternalCaller, make_internal_caller_dep
from pkg.jwt_auth import CurrentUser, make_current_user_dep
from services.user_service.app.config import UserServiceSettings, get_settings
from services.user_service.app.services.profiles import ProfileService


class UserDeps:
    session_factory: async_sessionmaker[AsyncSession] | None = None


deps = UserDeps()

_settings = get_settings()
_current_user_resolver = make_current_user_dep(_settings)
_internal_caller_resolver = make_internal_caller_dep(_settings, "user-service", "auth-service")


async def get_session() -> AsyncIterator[AsyncSession]:
    assert deps.session_factory is not None, "session factory not initialised"
    async with deps.session_factory() as session:
        yield session


def get_profile_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileService:
    return ProfileService(session)


CurrentUserDep = Annotated[CurrentUser, Depends(_current_user_resolver)]
InternalCallerDep = Annotated[InternalCaller, Depends(_internal_caller_resolver)]


def get_app_settings() -> UserServiceSettings:
    return _settings
