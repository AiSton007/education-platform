"""User profile endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from pkg.errors import Forbidden
from services.user_service.app.deps import (
    CurrentUserDep,
    InternalCallerDep,
    get_profile_service,
)
from services.user_service.app.schemas import (
    ProfileInternalCreate,
    ProfileOut,
    ProfilePatch,
    ProfilesList,
    ProfileStatusOut,
)
from services.user_service.app.services.profiles import ProfileService

router = APIRouter(prefix="/api/v1/users", tags=["users"])

_AUTHORS = {"admin", "manager"}
_ADMIN_ONLY = {"admin"}


@router.get("/me", response_model=ProfileOut)
async def get_me(
    user: CurrentUserDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileOut:
    profile = await service.get(uuid.UUID(user.id))
    return ProfileOut.model_validate(profile)


@router.get("", response_model=ProfilesList)
async def list_profiles(
    user: CurrentUserDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProfilesList:
    if user.role not in _AUTHORS:
        raise Forbidden("Only managers and admins can list users")
    items, total = await service.list(limit=limit, offset=offset)
    return ProfilesList(
        items=[ProfileOut.model_validate(p) for p in items],
        total=total,
    )


@router.get("/{user_id}", response_model=ProfileOut)
async def get_profile(
    user_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileOut:
    if user.role not in _AUTHORS and str(user_id) != user.id:
        raise Forbidden("Cannot view foreign profile")
    profile = await service.get(user_id)
    return ProfileOut.model_validate(profile)


@router.patch("/{user_id}", response_model=ProfileOut)
async def patch_profile(
    user_id: uuid.UUID,
    payload: ProfilePatch,
    user: CurrentUserDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileOut:
    if user.role not in _AUTHORS and str(user_id) != user.id:
        raise Forbidden("Cannot edit foreign profile")
    if payload.role is not None and user.role not in _ADMIN_ONLY:
        raise Forbidden("Only admin can change role")
    if payload.is_active is not None and user.role not in _ADMIN_ONLY:
        raise Forbidden("Only admin can change is_active")
    profile = await service.patch(user_id, fields=payload.model_dump(exclude_unset=True))
    return ProfileOut.model_validate(profile)


@router.delete("/{user_id}", response_model=ProfileOut)
async def deactivate_profile(
    user_id: uuid.UUID,
    user: CurrentUserDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileOut:
    """Soft-delete: marks the profile as inactive (admin-only)."""
    if user.role not in _ADMIN_ONLY:
        raise Forbidden("Only admin can deactivate users")
    profile = await service.deactivate(user_id)
    return ProfileOut.model_validate(profile)


@router.post(
    "/internal",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileOut,
    include_in_schema=False,
)
async def create_profile_internal(
    payload: ProfileInternalCreate,
    _: InternalCallerDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileOut:
    profile = await service.create_internal(
        user_id=payload.user_id,
        email=payload.email,
        full_name=payload.full_name,
        department=payload.department,
        position=payload.position,
        role=payload.role,
    )
    return ProfileOut.model_validate(profile)


@router.get(
    "/internal/{user_id}",
    response_model=ProfileOut,
    include_in_schema=False,
)
async def get_profile_internal(
    user_id: uuid.UUID,
    _: InternalCallerDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileOut:
    profile = await service.get(user_id)
    return ProfileOut.model_validate(profile)


@router.get(
    "/internal/{user_id}/status",
    response_model=ProfileStatusOut,
    include_in_schema=False,
)
async def get_profile_status_internal(
    user_id: uuid.UUID,
    _: InternalCallerDep,
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileStatusOut:
    """Minimal status lookup used by auth-service during login."""
    profile = await service.get(user_id)
    return ProfileStatusOut.model_validate(profile)
