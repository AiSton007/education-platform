"""HTTP client to report-service (uses internal JWT)."""

from __future__ import annotations

from typing import Any

from pkg.errors import UpstreamError
from pkg.http_client import internal_client
from pkg.internal_auth import InternalIssuer


class ReportServiceClient:
    def __init__(self, *, base_url: str, issuer: InternalIssuer) -> None:
        self._base_url = base_url
        self._issuer = issuer

    async def create_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with internal_client(self._base_url, "report-service", self._issuer) as client:
            response = await client.post("/api/v1/reports", json=payload)
            if response.status_code not in (200, 201):
                raise UpstreamError(
                    message=f"report-service rejected create: {response.status_code}",
                    details={"status": response.status_code, "body": response.text[:500]},
                )
            return response.json()
