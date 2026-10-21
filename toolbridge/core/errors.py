"""Normalized exceptions used within the MCP core."""

from typing import Any

from toolbridge.core.contracts import ErrorCode


class ToolBridgeError(Exception):
    """Base error with safe client-facing metadata."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class DuplicateToolError(ToolBridgeError):
    """Raised when a registry receives an existing tool name."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            ErrorCode.DUPLICATE_TOOL,
            "A tool with this name is already registered.",
            details={"tool_name": tool_name},
        )


class ToolNotFoundError(ToolBridgeError):
    """Raised when a requested tool is not registered."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            ErrorCode.TOOL_NOT_FOUND,
            "The requested tool is not available.",
            details={"tool_name": tool_name},
        )


class RequestValidationError(ToolBridgeError):
    """Raised when a request or tool input does not match its contract."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.INVALID_REQUEST, message, details=details)


class ToolExecutionTimeoutError(ToolBridgeError):
    """Raised when a tool exceeds its approved execution time."""

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            ErrorCode.EXECUTION_TIMEOUT,
            "The tool did not complete within its time limit.",
            retryable=True,
            details={"timeout_seconds": timeout_seconds},
        )


class ToolExecutionFailedError(ToolBridgeError):
    """Raised when a tool fails unexpectedly."""

    def __init__(self) -> None:
        super().__init__(
            ErrorCode.EXECUTION_FAILED,
            "The tool could not complete the request.",
        )


class ResponseValidationError(ToolBridgeError):
    """Raised when tool output violates its declared contract."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(ErrorCode.INVALID_RESPONSE, message, details=details)
