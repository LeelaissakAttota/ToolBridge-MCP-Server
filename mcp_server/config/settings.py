"""Application settings using Pydantic v2.

This module defines a ``Settings`` class that reads environment variables
and provides defaults for configuration values required by the server.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values for the MCP server.

    The class automatically reads from ``.env`` files and the process
    environment. Extend with additional fields as the project evolves.
    """

    # Example fields – replace or extend as needed
    APP_NAME: str = Field(default="toolbridge-mcp-server", description="Application name")
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level for the server")
    HOST: str = Field(default="0.0.0.0", description="Host interface to bind")
    PORT: int = Field(default=8000, description="Port number for the HTTP server")

    # Provider API keys
    CEREBRAS_API_KEY: str = Field(default="", description="Cerebras API key")
    NVIDIA_API_KEY: str = Field(default="", description="NVIDIA API key")
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key")

    # Provider routing configuration
    DEFAULT_PROVIDER: str = Field(default="openrouter", description="Default LLM provider")
    DEFAULT_MODEL: str = Field(default="", description="Default model name")
    FAST_PROVIDER: str = Field(default="cerebras", description="Fast path provider")
    FAST_MODEL: str = Field(default="llama3.1-8b", description="Fast path model")
    SMART_PROVIDER: str = Field(default="openrouter", description="Smart path provider")
    SMART_MODEL: str = Field(default="claude-3.5-sonnet", description="Smart path model")
    FALLBACK_PROVIDER: str = Field(default="nvidia", description="Fallback provider")
    ENABLE_FAILOVER: bool = Field(default=True, description="Enable automatic failover")

    # Request configuration
    REQUEST_TIMEOUT: float = Field(default=30.0, description="Request timeout in seconds")
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Export a singleton that can be imported throughout the project
settings = Settings()