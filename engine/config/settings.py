"""
ShipFaster Application Settings.

Centralized Pydantic V2 settings with environment variable loading.
All configuration is typed and validated at startup.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="shipfaster")
    user: str = Field(default="shipfaster")
    password: str = Field(default="shipfaster")
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=40)
    pool_timeout: int = Field(default=30)
    echo: bool = Field(default=False)

    @property
    def async_url(self) -> str:
        """Async PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """Sync PostgreSQL connection URL (for Alembic)."""
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    password: str | None = Field(default=None)
    db: int = Field(default=0)
    max_connections: int = Field(default=50)

    @property
    def url(self) -> str:
        """Redis connection URL."""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class MinIOSettings(BaseSettings):
    """MinIO / S3-compatible object storage settings."""

    model_config = SettingsConfigDict(env_prefix="MINIO_", extra="ignore")

    endpoint: str = Field(default="localhost:9000")
    access_key: str = Field(default="minioadmin")
    secret_key: str = Field(default="minioadmin")
    bucket: str = Field(default="shipfaster-artifacts")
    secure: bool = Field(default=False)

    @property
    def endpoint_url(self) -> str:
        """Full endpoint URL."""
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}"


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    google_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    default_model: str = Field(default="gemini-1.5-pro")
    max_retries: int = Field(default=3)
    timeout_seconds: int = Field(default=120)
    max_tokens: int = Field(default=8192)


class GitHubSettings(BaseSettings):
    """GitHub App / Webhook settings."""

    model_config = SettingsConfigDict(env_prefix="GITHUB_", extra="ignore")

    app_id: str = Field(default="")
    private_key: str = Field(default="")
    webhook_secret: str = Field(default="")


class ViaSocketSettings(BaseSettings):
    """viaSocket integration settings."""

    model_config = SettingsConfigDict(env_prefix="VIASOCKET_", extra="ignore")

    max_retries: int = Field(default=3)
    timeout_seconds: int = Field(default=30)
    retry_backoff_base: float = Field(default=2.0)


class SecuritySettings(BaseSettings):
    """Security and API key settings."""

    model_config = SettingsConfigDict(env_prefix="SECURITY_", extra="ignore")

    api_key_hash_algorithm: str = Field(default="sha256")
    api_key_length: int = Field(default=64)
    secret_key: str = Field(default="CHANGE_ME_IN_PRODUCTION_AT_LEAST_32_CHARS")


class Settings(BaseSettings):
    """
    Root application settings.

    Composed from environment variables and sub-setting groups.
    All settings are validated at startup — the app will not start
    with invalid configuration.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = Field(default="ShipFaster")
    app_version: str = Field(default="1.0.0")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    allowed_hosts: list[str] = Field(default=["*"])
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # --- Sandbox ---
    sandbox_enabled: bool = Field(default=True)
    sandbox_timeout_seconds: int = Field(default=30)
    sandbox_use_docker: bool = Field(default=False)

    # --- Sub-settings (instantiated inline) ---
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    minio: MinIOSettings = Field(default_factory=MinIOSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    github: GitHubSettings = Field(default_factory=GitHubSettings)
    viasocket: ViaSocketSettings = Field(default_factory=ViaSocketSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    Use this everywhere instead of instantiating Settings() directly.
    The @lru_cache ensures settings are loaded and validated only once.
    """
    return Settings()
