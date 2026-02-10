from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SAP v3"
    app_env: Literal["development", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    debug: bool = False

    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"])

    database_url: str = "sqlite+aiosqlite:///./sapv3.db"

    secret_key: str = "changeme_to_64_characters_minimum_for_dev_only"
    access_token_expire_minutes: int = 15
    refresh_token_expire_hours: int = 8

    session_idle_timeout_minutes: int = 30
    max_concurrent_sessions: int = 3

    file_storage_path: str = "backend/uploads"
    max_file_size_mb: int = 50

    default_extraction_confidence: float = 0.95

    sentry_dsn: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
