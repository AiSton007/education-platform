"""Service-specific settings for ``api-gateway``."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pkg.config import BaseAppSettings, JWTSettings


class GatewaySettings(BaseAppSettings, JWTSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_name: str = Field(default="api-gateway", validation_alias="APP_NAME")

    auth_service_url: str = Field(default="http://auth-service:8080", validation_alias="AUTH_SERVICE_URL")
    user_service_url: str = Field(default="http://user-service:8080", validation_alias="USER_SERVICE_URL")
    test_service_url: str = Field(default="http://test-service:8080", validation_alias="TEST_SERVICE_URL")
    report_service_url: str = Field(
        default="http://report-service:8080", validation_alias="REPORT_SERVICE_URL"
    )

    proxy_timeout_seconds: float = Field(default=30.0, validation_alias="PROXY_TIMEOUT_SECONDS")


_settings: GatewaySettings | None = None


def get_settings() -> GatewaySettings:
    global _settings
    if _settings is None:
        _settings = GatewaySettings()
    return _settings
