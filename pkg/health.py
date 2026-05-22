"""Readiness probes — composable async callables used by ``pkg.app_factory``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncEngine

from pkg.db import ping

ReadyCheck = Callable[[], Awaitable[None]]


def db_ready(engine: AsyncEngine) -> ReadyCheck:
    async def _check() -> None:
        await ping(engine)

    return _check


def always_ready() -> ReadyCheck:
    async def _check() -> None:
        return None

    return _check
