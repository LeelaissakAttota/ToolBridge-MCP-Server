"""Base Pydantic models for the ToolBridge MCP Server.

All domain models should inherit from :class:`BaseModel` defined here to
ensure consistent configuration and future extensions such as custom
encoders/decoders.
"""

from pydantic import BaseModel

class BaseModelConfig(BaseModel):
    """Root model for all data structures.

    Currently a thin wrapper around :class:`pydantic.BaseModel` but provides a
    central place for future customizations (e.g., custom JSON encoders).
    """
    pass

# Export the name expected by other modules
__all__ = ["BaseModelConfig"]
