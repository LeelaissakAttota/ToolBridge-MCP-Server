"""Stable contracts shared by MCP core services."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from re import compile as compile_pattern
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

TOOL_NAME_PATTERN = compile_pattern(r"^[a-z][a-z0-9_]{0,63}$")
CORRELATION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"


class ToolInput(BaseModel):
    """Base model for tool input with unknown fields forbidden."""

    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyToolInput(ToolInput):
    """Input contract for tools that accept no arguments."""


class ToolOutput(BaseModel):
    """Base model for validated, structured tool output."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ErrorCode(StrEnum):
    """Stable client-facing MCP core error categories."""

    INVALID_REQUEST = "invalid_request"
    TOOL_NOT_FOUND = "tool_not_found"
    DUPLICATE_TOOL = "duplicate_tool"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_CANCELLED = "execution_cancelled"
    EXECUTION_FAILED = "execution_failed"
    INVALID_RESPONSE = "invalid_response"
    INVALID_SYMBOL = "invalid_symbol"
    DATA_SOURCE_UNAVAILABLE = "data_source_unavailable"
    WEBSITE_UNAVAILABLE = "website_unavailable"
    DATABASE_QUERY_FAILED = "database_query_failed"
    FILE_ANALYSIS_FAILED = "file_analysis_failed"
    CURRENCY_RATE_UNAVAILABLE = "currency_rate_unavailable"
    LLM_ANALYSIS_UNAVAILABLE = "llm_analysis_unavailable"


class ToolErrorDetail(BaseModel):
    """Safe error information that may be returned to a client."""

    model_config = ConfigDict(extra="forbid", strict=True)

    code: ErrorCode
    message: str = Field(min_length=1, max_length=256)
    retryable: bool = False
    correlation_id: str = Field(pattern=CORRELATION_ID_PATTERN)
    details: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRequest(BaseModel):
    """Validated request passed to the execution service."""

    model_config = ConfigDict(extra="forbid", strict=True)

    tool_name: str = Field(min_length=1, max_length=64, pattern=TOOL_NAME_PATTERN.pattern)
    arguments: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(pattern=CORRELATION_ID_PATTERN)


class ToolExecutionResponse(BaseModel):
    """Normalized success or failure returned by the execution service."""

    model_config = ConfigDict(extra="forbid", strict=True)

    tool_name: str | None = None
    correlation_id: str = Field(pattern=CORRELATION_ID_PATTERN)
    success: bool
    duration_ms: float = Field(ge=0)
    result: dict[str, Any] | None = None
    error: ToolErrorDetail | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> "ToolExecutionResponse":
        """Require exactly one of result or error for each outcome."""

        if self.success and (self.result is None or self.error is not None):
            raise ValueError("successful responses require a result and no error")
        if not self.success and (self.error is None or self.result is not None):
            raise ValueError("failed responses require an error and no result")
        return self


class ToolMetadata(BaseModel):
    """Validated discovery information for one registered tool."""

    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=64, pattern=TOOL_NAME_PATTERN.pattern)
    description: str = Field(min_length=1, max_length=1024)
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_seconds: float = Field(gt=0, le=300)


# Handlers accept their own ToolInput subclass; Callable is contravariant, so Any here.
ToolHandler = Callable[[Any], object | Awaitable[object]]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Immutable tool contract and handler registration."""

    name: str
    description: str
    input_model: type[ToolInput]
    output_model: type[ToolOutput]
    handler: ToolHandler
    timeout_seconds: float

    def __post_init__(self) -> None:
        """Reject invalid definitions before they enter the registry."""

        if TOOL_NAME_PATTERN.fullmatch(self.name) is None:
            raise ValueError(f"invalid tool name: {self.name!r}")
        if not self.description.strip() or len(self.description) > 1024:
            raise ValueError("tool description must contain 1 to 1024 characters")
        if not issubclass(self.input_model, ToolInput):
            raise TypeError("input_model must inherit ToolInput")
        if not issubclass(self.output_model, ToolOutput):
            raise TypeError("output_model must inherit ToolOutput")
        if not callable(self.handler):
            raise TypeError("handler must be callable")
        if not 0 < self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be greater than 0 and at most 300")

    def metadata(self) -> ToolMetadata:
        """Build the validated public discovery contract."""

        return ToolMetadata(
            name=self.name,
            description=self.description.strip(),
            input_schema=self.input_model.model_json_schema(),
            output_schema=self.output_model.model_json_schema(),
            timeout_seconds=self.timeout_seconds,
        )
