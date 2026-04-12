"""
Deployment configuration for the Document Encryption microservice.
Reads all settings from environment variables (injected by Railway or .env for local dev).
Crypto constants live in config/settings.py and config/constants.py — not here.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server
    port: int = Field(default=8000)
    host: str = Field(default="0.0.0.0")
    log_level: str = Field(default="INFO")

    # Feature flags
    enable_ui: bool = Field(default=True)

    # Storage
    temp_dir: str = Field(default="/tmp/enc_service")
    max_file_size_mb: int = Field(default=50, ge=1, le=500)

    # CORS
    cors_origins: str = Field(default="*")

    # Cleanup TTL
    file_ttl_seconds: int = Field(default=3600, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # PORT and port both resolve
        extra="ignore",         # Railway injects extra vars we don't care about
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance. Cache is cleared in tests via get_settings.cache_clear()."""
    return Settings()
