"""Service-specific settings for ``auth-service``."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pkg.config import BaseAppSettings, DatabaseSettings, InternalJWTSettings, JWTSettings


class AuthServiceSettings(BaseAppSettings, DatabaseSettings, JWTSettings, InternalJWTSettings):
    """Aggregated settings for the auth service."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_name: str = Field(default="auth-service", validation_alias="APP_NAME")
    db_schema: str = Field(default="auth", validation_alias="DB_SCHEMA")

    user_service_url: str = Field(
        default="http://user-service:8080",
        validation_alias="USER_SERVICE_URL",
    )

    bcrypt_rounds: int = Field(default=12, validation_alias="BCRYPT_ROUNDS")


_settings: AuthServiceSettings | None = None


def get_settings() -> AuthServiceSettings:
    global _settings
    if _settings is None:
        _settings = AuthServiceSettings()
    return _settings
