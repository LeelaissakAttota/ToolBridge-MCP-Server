"""Application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TOOLBRIDGE_",
        extra="ignore",
    )

    app_name: str = "ToolBridge MCP Server"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    tool_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_request_bytes: int = Field(default=65_536, ge=1_024, le=10_485_760)
    max_response_bytes: int = Field(default=262_144, ge=1_024, le=10_485_760)


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for the current process."""

    return Settings()

