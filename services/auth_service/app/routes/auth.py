"""HTTP endpoints for ``auth-service``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from pkg.errors import Forbidden
from services.auth_service.app.deps import CurrentUserDep, get_auth_service
from services.auth_service.app.models import UserRole
from services.auth_service.app.schemas import (
    AdminResetPasswordIn,
    AdminResetPasswordOut,
    LoginIn,
    MeOut,
    RefreshIn,
    RegisterIn,
    TokenPair,
    UserOut,
)
from services.auth_service.app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(
    payload: RegisterIn,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserOut:
    user = await service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        department=payload.department,
        position=payload.position,
        role=UserRole.EMPLOYEE,
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    payload: LoginIn,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    _, access, refresh, access_ttl, refresh_ttl = await service.login(
        email=payload.email, password=payload.password
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        access_expires_in=access_ttl,
        refresh_expires_in=refresh_ttl,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    payload: RefreshIn,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenPair:
    _, access, refresh_token, access_ttl, refresh_ttl = await service.refresh(
        refresh_token=payload.refresh_token,
    )
    return TokenPair(
        access_token=access,
        refresh_token=refresh_token,
        access_expires_in=access_ttl,
        refresh_expires_in=refresh_ttl,
    )


@router.get("/me", response_model=MeOut)
async def me(
    user: CurrentUserDep,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> MeOut:
    record = await service.get_user(uuid.UUID(user.id))
    return MeOut.model_validate(record)


@router.post("/admin/reset-password", response_model=AdminResetPasswordOut)
async def admin_reset_password(
    payload: AdminResetPasswordIn,
    user: CurrentUserDep,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AdminResetPasswordOut:
    """Forcibly set a new password for the given user (admin-only).

    All existing refresh tokens are revoked so the user must log in with the new password.
    """
    if user.role != "admin":
        raise Forbidden("Only admin can reset passwords")
    await service.reset_password(user_id=payload.user_id, new_password=payload.new_password)
    return AdminResetPasswordOut(user_id=payload.user_id)
