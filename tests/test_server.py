"""Tests for server module."""

from mcp_server.server import create_app


def test_create_app_returns_dict():
    """create_app should return a dict with expected keys."""
    app = create_app()
    assert isinstance(app, dict)
    assert "name" in app
    assert "debug" in app
    assert app["name"] == "toolbridge-mcp-server"
    assert app["debug"] is False


def test_create_app_logs_initialization(caplog):
    """create_app should log initialization message."""
    import logging
    caplog.set_level(logging.INFO)
    create_app()
    assert any("Initializing toolbridge-mcp-server" in record.message for record in caplog.records)