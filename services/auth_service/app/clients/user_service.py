"""Internal HTTP client used by auth-service to bootstrap profiles in user-service."""

from __future__ import annotations

import uuid

from pkg.errors import UpstreamError
from pkg.http_client import internal_client
from pkg.internal_auth import InternalIssuer


class UserServiceClient:
    """Thin wrapper around the user-service internal API."""

    def __init__(self, *, base_url: str, issuer: InternalIssuer) -> None:
        self._base_url = base_url
        self._issuer = issuer

    async def create_profile(
        self,
        *,
        user_id: uuid.UUID,
        email: str,
        full_name: str,
        department: str | None,
        position: str | None,
        role: str,
    ) -> None:
        payload = {
            "user_id": str(user_id),
            "email": email,
            "full_name": full_name,
            "department": department,
            "position": position,
            "role": role,
        }
        async with internal_client(
            self._base_url, audience="user-service", issuer=self._issuer
        ) as client:
            response = await client.post("/api/v1/users/internal", json=payload)
            if response.status_code not in (200, 201, 409):
                # 409 is treated as idempotent success — profile already exists
                raise UpstreamError(
                    message=f"user-service rejected profile creation: {response.status_code}",
                    details={"status": response.status_code, "body": response.text[:500]},
                )
