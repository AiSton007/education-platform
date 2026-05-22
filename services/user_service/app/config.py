"""Service-specific settings for ``user-service``."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pkg.config import BaseAppSettings, DatabaseSettings, InternalJWTSettings, JWTSettings


class UserServiceSettings(BaseAppSettings, DatabaseSettings, JWTSettings, InternalJWTSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_name: str = Field(default="user-service", validation_alias="APP_NAME")
    db_schema: str = Field(default="users", validation_alias="DB_SCHEMA")


_settings: UserServiceSettings | None = None


def get_settings() -> UserServiceSettings:
    global _settings
    if _settings is None:
        _settings = UserServiceSettings()
    return _settings
