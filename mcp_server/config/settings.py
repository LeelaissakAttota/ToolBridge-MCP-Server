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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Export a singleton that can be imported throughout the project
settings = Settings()