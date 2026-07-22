"""Tests for logging module."""

import logging
from mcp_server.logging.logger import logger


def test_logger_exists():
    """Logger should be a logging.Logger instance."""
    assert isinstance(logger, logging.Logger)


def test_logger_name():
    """Logger name should match app name from settings."""
    from mcp_server.config import settings
    assert logger.name == settings.APP_NAME


def test_logger_level():
    """Logger level should respect LOG_LEVEL setting."""
    from mcp_server.config import settings
    assert logger.level == getattr(logging, settings.LOG_LEVEL)


def test_logger_has_handler():
    """Logger should have at least one handler (console)."""
    assert len(logger.handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)