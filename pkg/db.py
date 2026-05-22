"""Async SQLAlchemy engine/session factory shared by every backend service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from pkg.config import DatabaseSettings


def build_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create an :class:`AsyncEngine` with pool sizing taken from environment variables."""
    return create_async_engine(
        settings.async_dsn,
        pool_size=settings.db_max_idle_conns,
        max_overflow=max(settings.db_max_open_conns - settings.db_max_idle_conns, 0),
        pool_recycle=settings.db_conn_max_lifetime,
        pool_pre_ping=True,
        connect_args={"server_settings": {"search_path": settings.db_schema}}
        if settings.db_schema and settings.db_schema != "public"
        else {},
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def ping(engine: AsyncEngine) -> None:
    """Quick readiness check — opens a connection and executes ``SELECT 1``."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


def make_session_dep(session_factory: async_sessionmaker[AsyncSession]):
    """Return a FastAPI dependency that yields an :class:`AsyncSession`."""

    async def _dep() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    return _dep
