"""Tests for configuration loading."""

import os
from mcp_server.config.settings import Settings


def test_settings_defaults():
    """Settings should have sensible defaults."""
    settings = Settings()
    assert settings.APP_NAME == "toolbridge-mcp-server"
    assert settings.DEBUG is False
    assert settings.LOG_LEVEL == "INFO"
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000


def test_settings_env_override(monkeypatch):
    """Environment variables should override defaults."""
    monkeypatch.setenv("APP_NAME", "custom-app")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("HOST", "127.0.0.1")
    monkeypatch.setenv("PORT", "9000")

    settings = Settings()
    assert settings.APP_NAME == "custom-app"
    assert settings.DEBUG is True
    assert settings.LOG_LEVEL == "DEBUG"
    assert settings.HOST == "127.0.0.1"
    assert settings.PORT == 9000


def test_settings_singleton():
    """The exported singleton should be a Settings instance."""
    from mcp_server.config import settings
    assert isinstance(settings, Settings)
    assert settings.APP_NAME == "toolbridge-mcp-server"