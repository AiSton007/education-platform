"""HTTP client to llm-service (uses internal JWT)."""

from __future__ import annotations

from typing import Any

import httpx

from pkg.errors import UpstreamError
from pkg.http_client import internal_client
from pkg.internal_auth import InternalIssuer


class LlmServiceClient:
    def __init__(
        self,
        *,
        base_url: str,
        issuer: InternalIssuer,
        analyze_timeout_seconds: float = 90.0,
    ) -> None:
        self._base_url = base_url
        self._issuer = issuer
        self._analyze_timeout = httpx.Timeout(
            connect=5.0,
            read=analyze_timeout_seconds,
            write=30.0,
            pool=5.0,
        )

    async def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with internal_client(
            self._base_url,
            "llm-service",
            self._issuer,
            request_timeout=self._analyze_timeout,
        ) as client:
            response = await client.post("/api/v1/analyze", json=payload)
            if response.status_code not in (200, 201, 202):
                raise UpstreamError(
                    message=f"llm-service rejected analyze: {response.status_code}",
                    details={"status": response.status_code, "body": response.text[:500]},
                )
            return response.json()
