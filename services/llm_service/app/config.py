"""Service-specific settings for ``llm-service``."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from pkg.config import BaseAppSettings, DatabaseSettings, InternalJWTSettings


class LlmServiceSettings(BaseAppSettings, DatabaseSettings, InternalJWTSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    app_name: str = Field(default="llm-service", validation_alias="APP_NAME")
    db_schema: str = Field(default="llm", validation_alias="DB_SCHEMA")

    llm_provider: str = Field(default="mock", validation_alias="LLM_PROVIDER")
    llm_api_url: str = Field(
        default="https://gigachat.devices.sberbank.ru/api/v1", validation_alias="LLM_API_URL"
    )
    llm_oauth_url: str = Field(
        default="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
        validation_alias="LLM_OAUTH_URL",
    )
    llm_oauth_scope: str = Field(default="GIGACHAT_API_PERS", validation_alias="LLM_OAUTH_SCOPE")
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_model: str = Field(default="GigaChat", validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_verify_ssl: bool = Field(default=True, validation_alias="LLM_VERIFY_SSL")


_settings: LlmServiceSettings | None = None


def get_settings() -> LlmServiceSettings:
    global _settings
    if _settings is None:
        _settings = LlmServiceSettings()
    return _settings
