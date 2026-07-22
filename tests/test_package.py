"""Tests for package initialization and exceptions."""

from mcp_server import __version__
from mcp_server.exceptions import ToolBridgeError, ConfigurationError, ProviderError


def test_package_version():
    """Package should expose a version string."""
    assert isinstance(__version__, str)
    assert __version__ == "0.3.0"


def test_exception_hierarchy():
    """All custom exceptions should inherit from ToolBridgeError."""
    assert issubclass(ConfigurationError, ToolBridgeError)
    assert issubclass(ProviderError, ToolBridgeError)
    assert issubclass(ToolBridgeError, Exception)


def test_exceptions_can_be_raised():
    """All exception classes should be raisable."""
    try:
        raise ConfigurationError("config failed")
    except ToolBridgeError:
        pass

    try:
        raise ProviderError("provider failed")
    except ToolBridgeError:
        pass

    try:
        raise ToolBridgeError("base error")
    except Exception:
        pass