"""Exception hierarchy for the ToolBridge MCP Server.

All custom exceptions inherit from :class:`ToolBridgeError` which itself
subclasses :class:`Exception`. This provides a single catch‑all for
application‑specific error handling.
"""

class ToolBridgeError(Exception):
    """Base class for all custom errors in the project."""

class ConfigurationError(ToolBridgeError):
    """Raised when configuration loading fails or is invalid."""

class ProviderError(ToolBridgeError):
    """Raised for errors originating from provider implementations."""

# Additional domain‑specific exceptions can be added here as the project
# grows.
