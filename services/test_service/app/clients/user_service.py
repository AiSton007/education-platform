"""HTTP client to user-service (uses internal JWT)."""

from __future__ import annotations

import uuid
from typing import Any

from pkg.errors import UpstreamError
from pkg.http_client import internal_client
from pkg.internal_auth import InternalIssuer


class UserServiceClient:
    def __init__(self, *, base_url: str, issuer: InternalIssuer) -> None:
        self._base_url = base_url
        self._issuer = issuer

    async def get_profile(self, user_id: uuid.UUID) -> dict[str, Any]:
        async with internal_client(self._base_url, "user-service", self._issuer) as client:
            response = await client.get(f"/api/v1/users/internal/{user_id}")
            if response.status_code != 200:
                raise UpstreamError(
                    message=f"user-service profile lookup failed: {response.status_code}",
                    details={"status": response.status_code, "body": response.text[:500]},
                )
            return response.json()
