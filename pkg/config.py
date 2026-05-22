"""Common pydantic-settings base for all microservices.

Each service subclasses :class:`BaseAppSettings` and adds its own fields.
All settings are loaded from environment variables (12-factor compliant).
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Settings shared by every service in the platform."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="service", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    app_port: int = Field(default=8080, validation_alias="APP_PORT")
    log_level: str = Field(default="info", validation_alias="LOG_LEVEL")
    metrics_enabled: bool = Field(default=True, validation_alias="METRICS_ENABLED")

    cors_allow_origins: str = Field(default="*", validation_alias="CORS_ALLOW_ORIGINS")


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings.

    Used by services that need a database connection (every backend except api-gateway).
    """

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    db_host: str = Field(default="postgres", validation_alias="DB_HOST")
    db_port: int = Field(default=5432, validation_alias="DB_PORT")
    db_name: str = Field(default="education", validation_alias="DB_NAME")
    db_user: str = Field(validation_alias="DB_USER")
    db_password: str = Field(validation_alias="DB_PASSWORD")
    db_ssl_mode: str = Field(default="disable", validation_alias="DB_SSL_MODE")
    db_schema: str = Field(default="public", validation_alias="DB_SCHEMA")

    db_max_open_conns: int = Field(default=10, validation_alias="DB_MAX_OPEN_CONNS")
    db_max_idle_conns: int = Field(default=2, validation_alias="DB_MAX_IDLE_CONNS")
    db_conn_max_lifetime: int = Field(default=300, validation_alias="DB_CONN_MAX_LIFETIME")

    @property
    def async_dsn(self) -> str:
        """SQLAlchemy DSN for asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_dsn(self) -> str:
        """Sync DSN used by Alembic for autogenerate / online operations."""
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


class JWTSettings(BaseSettings):
    """User-facing JWT settings (issued by auth-service, validated by everyone)."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    jwt_secret: str = Field(validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_ttl: int = Field(default=900, validation_alias="JWT_ACCESS_TOKEN_TTL")
    jwt_refresh_token_ttl: int = Field(default=604800, validation_alias="JWT_REFRESH_TOKEN_TTL")
    jwt_issuer: str = Field(default="education-platform", validation_alias="JWT_ISSUER")


class InternalJWTSettings(BaseSettings):
    """Service-to-service JWT settings (separate secret from user JWT)."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    internal_jwt_secret: str = Field(validation_alias="INTERNAL_JWT_SECRET")
    internal_jwt_algorithm: str = Field(default="HS256", validation_alias="INTERNAL_JWT_ALGORITHM")
    internal_jwt_ttl: int = Field(default=300, validation_alias="INTERNAL_JWT_TTL")
