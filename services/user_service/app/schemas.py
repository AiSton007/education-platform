"""Pydantic DTOs for ``user-service``."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from services.user_service.app.models import Role


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    department: str | None
    position: str | None
    role: Role
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProfilePatch(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    position: str | None = Field(default=None, max_length=255)
    role: Role | None = None
    is_active: bool | None = None


class ProfileInternalCreate(BaseModel):
    """Payload accepted from auth-service via internal JWT."""

    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    department: str | None = None
    position: str | None = None
    role: Role = Role.EMPLOYEE


class ProfileStatusOut(BaseModel):
    """Minimal status response used by auth-service during login (internal-only)."""

    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    is_active: bool
    role: Role


class ProfilesList(BaseModel):
    items: list[ProfileOut]
    total: int
