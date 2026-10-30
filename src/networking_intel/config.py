from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_PASSWORD_MARKER = "local-development-only"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "production"] = "local"
    # "demo": the database was seeded from the frozen snapshot in the repository
    # (no live refresh); every screen shows a DEMO badge with the snapshot date.
    app_data_mode: Literal["live", "demo"] = "live"
    database_url: str = Field(
        default="postgresql+psycopg://networking:local-development-only-change-me@localhost:5432/networking"
    )
    etl_input_path: Path = Path("data/staging/pilot_accounts.csv")

    # API — comma-separated lists keep .env files simple.
    api_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    api_trusted_hosts: str = "localhost,127.0.0.1"
    api_rate_limit_per_minute: int = Field(default=600, ge=1, le=10_000)
    api_docs_enabled: bool | None = None
    api_statement_timeout_ms: int = Field(default=5_000, ge=100, le=60_000)
    api_connect_timeout_s: int = Field(default=3, ge=1, le=30)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def production_is_locked_down(self) -> Settings:
        if self.app_env != "production":
            return self
        if DEV_PASSWORD_MARKER in self.database_url:
            raise ValueError("production DATABASE_URL must not use the development password")
        if "*" in self.cors_origins or "*" in self.trusted_hosts:
            raise ValueError("production CORS origins and trusted hosts must be explicit")
        if any(origin.startswith("http://") for origin in self.cors_origins):
            raise ValueError("production CORS origins must use https")
        return self

    @staticmethod
    def _split(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return self._split(self.api_cors_origins)

    @property
    def trusted_hosts(self) -> list[str]:
        return self._split(self.api_trusted_hosts)

    @property
    def docs_enabled(self) -> bool:
        if self.api_docs_enabled is not None:
            return self.api_docs_enabled
        return self.app_env != "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
