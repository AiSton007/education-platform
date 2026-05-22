"""FastAPI dependency wiring for ``auth-service``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pkg.internal_auth import InternalIssuer
from pkg.jwt_auth import CurrentUser, make_current_user_dep
from services.auth_service.app.clients.user_service import UserServiceClient
from services.auth_service.app.config import AuthServiceSettings, get_settings
from services.auth_service.app.services.auth import AuthService


class AuthDeps:
    """Singletons populated at app startup."""

    session_factory: async_sessionmaker[AsyncSession] | None = None
    user_client: UserServiceClient | None = None
    issuer: InternalIssuer | None = None


deps = AuthDeps()

# Built once at startup so FastAPI can resolve dependencies without recreating closures.
_current_user_resolver = make_current_user_dep(get_settings())


async def get_session() -> AsyncIterator[AsyncSession]:
    assert deps.session_factory is not None, "session factory not initialised"
    async with deps.session_factory() as session:
        yield session


def get_user_client() -> UserServiceClient:
    assert deps.user_client is not None, "user client not initialised"
    return deps.user_client


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[AuthServiceSettings, Depends(get_settings)],
    user_client: Annotated[UserServiceClient, Depends(get_user_client)],
) -> AuthService:
    return AuthService(session=session, settings=settings, user_service_client=user_client)


CurrentUserDep = Annotated[CurrentUser, Depends(_current_user_resolver)]
