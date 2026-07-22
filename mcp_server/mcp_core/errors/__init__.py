"""MCP-specific exception classes.

This module defines all custom exceptions used by the MCP Core Engine,
following JSON-RPC 2.0 error codes where applicable.
"""

from __future__ import annotations


class MCPError(Exception):
    """Base class for all MCP-specific errors.

    All MCP errors inherit from this class to allow catching
    MCP-specific errors separately from other exceptions.
    """

    def __init__(
        self,
        message: str,
        code: int = -32000,
        data: dict | None = None,
    ):
        """Initialize MCP error.

        Args:
            message: Human-readable error message.
            code: JSON-RPC 2.0 error code (default: -32000 for server error).
            data: Optional additional error data.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}

    def to_json_rpc_error(self) -> dict:
        """Convert to JSON-RPC 2.0 error object."""
        error = {"code": self.code, "message": self.message}
        if self.data:
            error["data"] = self.data
        return error


class InvalidRequest(MCPError):
    """Invalid JSON-RPC request (parse error or malformed).

    JSON-RPC 2.0 error code: -32600
    """

    def __init__(self, message: str = "Invalid request", data: dict | None = None):
        super().__init__(message, code=-32600, data=data)


class MethodNotFound(MCPError):
    """Method not found on server.

    JSON-RPC 2.0 error code: -32601
    """

    def __init__(self, method: str, data: dict | None = None):
        message = f"Method not found: {method}"
        error_data = {"method": method}
        if data:
            error_data.update(data)
        super().__init__(message, code=-32601, data=error_data)


class InvalidParams(MCPError):
    """Invalid method parameters.

    JSON-RPC 2.0 error code: -32602
    """

    def __init__(self, message: str = "Invalid parameters", data: dict | None = None):
        super().__init__(message, code=-32602, data=data)


class InternalError(MCPError):
    """Internal server error.

    JSON-RPC 2.0 error code: -32603
    """

    def __init__(self, message: str = "Internal error", data: dict | None = None):
        super().__init__(message, code=-32603, data=data)


class ServerError(MCPError):
    """Generic server error (reserved range -32000 to -32099)."""

    def __init__(self, message: str = "Server error", data: dict | None = None):
        super().__init__(message, code=-32000, data=data)


class ToolExecutionError(MCPError):
    """Error during tool execution.

    Not a JSON-RPC standard error; uses server error range.
    """

    def __init__(
        self,
        tool_name: str,
        message: str,
        data: dict | None = None,
    ):
        error_message = f"Tool execution failed: {tool_name} - {message}"
        error_data = {"tool_name": tool_name}
        if data:
            error_data.update(data)
        super().__init__(error_message, code=-32001, data=error_data)


class ToolNotFoundError(MCPError):
    """Tool not found in registry."""

    def __init__(self, tool_name: str):
        message = f"Tool not found: {tool_name}"
        super().__init__(message, code=-32002, data={"tool_name": tool_name})


class ToolValidationError(MCPError):
    """Tool schema validation failed."""

    def __init__(self, tool_name: str, message: str, data: dict | None = None):
        error_message = f"Tool validation failed: {tool_name} - {message}"
        error_data = {"tool_name": tool_name}
        if data:
            error_data.update(data)
        super().__init__(error_message, code=-32003, data=error_data)


class InitializationError(MCPError):
    """Server initialization failed."""

    def __init__(self, message: str = "Initialization failed", data: dict | None = None):
        super().__init__(message, code=-32004, data=data)


class HealthCheckError(MCPError):
    """Health check failed."""

    def __init__(self, message: str = "Health check failed", data: dict | None = None):
        super().__init__(message, code=-32005, data=data)