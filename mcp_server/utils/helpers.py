"""Utility helper functions for the ToolBridge MCP Server.

This module contains generic functions that do not belong to any specific
package but are useful across the codebase.
"""

def noop() -> None:
    """A no‑operation function used as a placeholder.

    ``noop`` can be imported where a callable is required but no action
    should be performed.
    """
    pass
