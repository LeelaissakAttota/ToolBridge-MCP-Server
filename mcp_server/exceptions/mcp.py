"""MCP-specific exceptions.

Defines standard JSON-RPC 2.0 and MCP protocol error codes.
"""

from typing import Any


class MCPError(Exception):
    """Base exception for all MCP errors."""

    def __init__(
        self,
        message: str,
        code: int = -32603,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}

    def to_json_rpc_error(self) -> dict[str, Any]:
        """Convert to JSON-RPC error object.

        Returns:
            Error dict compliant with JSON-RPC 2.0 spec.
        """
        error = {
            "code": self.code,
            "message": self.message,
        }
        if self.data:
            error["data"] = self.data
        return error


class InvalidRequest(MCPError):
    """Invalid JSON-RPC request (code -32600)."""

    def __init__(self, message: str = "Invalid request", data: dict[str, Any] | None = None):
        super().__init__(message, code=-32600, data=data)


class MethodNotFound(MCPError):
    """Method not found (code -32601)."""

    def __init__(self, method: str, data: dict[str, Any] | None = None):
        message = f"Method not found: {method}"
        super().__init__(message, code=-32601, data=data)


class InvalidParams(MCPError):
    """Invalid method parameters (code -32602)."""

    def __init__(self, message: str = "Invalid params", data: dict[str, Any] | None = None):
        super().__init__(message, code=-32602, data=data)


class InternalError(MCPError):
    """Internal JSON-RPC error (code -32603)."""

    def __init__(self, message: str = "Internal error", data: dict[str, Any] | None = None):
        super().__init__(message, code=-32603, data=data)


class ParseError(MCPError):
    """Parse error (code -32700)."""

    def __init__(self, message: str = "Parse error", data: dict[str, Any] | None = None):
        super().__init__(message, code=-32700, data=data)


# MCP-specific error codes (per MCP spec)
class ToolNotFound(MCPError):
    """Tool not found (code -32001)."""

    def __init__(self, name: str, data: dict[str, Any] | None = None):
        message = f"Tool not found: {name}"
        tool_data = {"tool_name": name}
        if data:
            tool_data.update(data)
        super().__init__(message, code=-32001, data=tool_data)


class ToolExecutionError(MCPError):
    """Tool execution failed (code -32002)."""

    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(message, code=-32002, data=data)


class ResourceNotFound(MCPError):
    """Resource not found (code -32003)."""

    def __init__(self, uri: str, data: dict[str, Any] | None = None):
        message = f"Resource not found: {uri}"
        super().__init__(message, code=-32003, data=data)


class PromptNotFound(MCPError):
    """Prompt not found (code -32004)."""

    def __init__(self, name: str, data: dict[str, Any] | None = None):
        message = f"Prompt not found: {name}"
        super().__init__(message, code=-32004, data=data)


class InvalidSchema(MCPError):
    """Invalid schema (code -32005)."""

    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(message, code=-32005, data=data)


class ServerNotInitialized(MCPError):
    """Server not initialized (code -32006)."""

    def __init__(self, message: str = "Server not initialized", data: dict[str, Any] | None = None):
        super().__init__(message, code=-32006, data=data)


# Error code to exception mapping
ERROR_CODE_MAP: dict[int, type[MCPError]] = {
    -32700: ParseError,
    -32600: InvalidRequest,
    -32601: MethodNotFound,
    -32602: InvalidParams,
    -32603: InternalError,
    -32001: ToolNotFound,
    -32002: ToolExecutionError,
    -32003: ResourceNotFound,
    -32004: PromptNotFound,
    -32005: InvalidSchema,
    -32006: ServerNotInitialized,
}


def create_mcp_error(code: int, message: str, data: dict[str, Any] | None = None) -> MCPError:
    """Create appropriate MCP error from code.

    Args:
        code: Error code.
        message: Error message.
        data: Optional error data.

    Returns:
        MCPError subclass instance.
    """
    error_class = ERROR_CODE_MAP.get(code, MCPError)
    if error_class is MCPError:
        # For unknown codes, use base MCPError with the provided code
        return MCPError(message, code=code, data=data)
    return error_class(message, data=data)