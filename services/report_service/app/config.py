"""Service-specific settings for ``report-service``."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pkg.config import BaseAppSettings, DatabaseSettings, InternalJWTSettings, JWTSettings


class ReportServiceSettings(BaseAppSettings, DatabaseSettings, JWTSettings, InternalJWTSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_name: str = Field(default="report-service", validation_alias="APP_NAME")
    db_schema: str = Field(default="reports", validation_alias="DB_SCHEMA")


_settings: ReportServiceSettings | None = None


def get_settings() -> ReportServiceSettings:
    global _settings
    if _settings is None:
        _settings = ReportServiceSettings()
    return _settings
