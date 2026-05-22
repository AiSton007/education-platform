"""Service-specific settings for ``test-service``."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pkg.config import BaseAppSettings, DatabaseSettings, InternalJWTSettings, JWTSettings


class TestServiceSettings(BaseAppSettings, DatabaseSettings, JWTSettings, InternalJWTSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_name: str = Field(default="test-service", validation_alias="APP_NAME")
    db_schema: str = Field(default="tests", validation_alias="DB_SCHEMA")

    llm_service_url: str = Field(default="http://llm-service:8080", validation_alias="LLM_SERVICE_URL")
    report_service_url: str = Field(
        default="http://report-service:8080", validation_alias="REPORT_SERVICE_URL"
    )


_settings: TestServiceSettings | None = None


def get_settings() -> TestServiceSettings:
    global _settings
    if _settings is None:
        _settings = TestServiceSettings()
    return _settings
