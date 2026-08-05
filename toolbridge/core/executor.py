"""Validated, observable execution boundary for registered tools."""

import asyncio
import inspect
from re import fullmatch
from time import perf_counter
from typing import Any, cast
from uuid import uuid4

from toolbridge.core.contracts import (
    CORRELATION_ID_PATTERN,
    TOOL_NAME_PATTERN,
    ErrorCode,
    ToolErrorDetail,
    ToolExecutionResponse,
    ToolHandler,
    ToolInput,
)
from toolbridge.core.errors import (
    ToolBridgeError,
    ToolExecutionFailedError,
    ToolExecutionTimeoutError,
)
from toolbridge.core.ports import ExecutionEventLogger, NullExecutionEventLogger
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator


class ToolExecutor:
    """Validate, execute, and normalize outcomes for registered tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        request_validator: RequestValidator,
        response_validator: ResponseValidator,
        event_logger: ExecutionEventLogger | None = None,
    ) -> None:
        self._registry = registry
        self._request_validator = request_validator
        self._response_validator = response_validator
        self._event_logger = event_logger or NullExecutionEventLogger()

    async def execute(
        self,
        tool_name: object,
        arguments: object,
        *,
        correlation_id: object | None = None,
    ) -> ToolExecutionResponse:
        """Execute a raw request and always return a validated safe outcome."""

        started_at = perf_counter()
        generated_id = uuid4().hex
        response_correlation_id = self._safe_correlation_id(
            correlation_id,
            fallback=generated_id,
        )
        response_tool_name = self._safe_tool_name(tool_name)

        try:
            request = self._request_validator.validate_request(
                tool_name=tool_name,
                arguments=arguments,
                correlation_id=correlation_id if correlation_id is not None else generated_id,
            )
            response_correlation_id = request.correlation_id
            response_tool_name = request.tool_name
            definition = self._registry.get(request.tool_name)
            self._event_logger.started(
                tool_name=request.tool_name,
                correlation_id=request.correlation_id,
            )
            validated_arguments = self._request_validator.validate_arguments(
                definition,
                request.arguments,
            )
            try:
                async with asyncio.timeout(definition.timeout_seconds):
                    raw_result = await self._invoke(
                        definition.handler,
                        validated_arguments,
                    )
            except TimeoutError as error:
                raise ToolExecutionTimeoutError(definition.timeout_seconds) from error
            result = self._response_validator.validate(definition, raw_result)
        except asyncio.CancelledError:
            duration_ms = self._duration_ms(started_at)
            self._event_logger.failed(
                tool_name=response_tool_name,
                correlation_id=response_correlation_id,
                duration_ms=duration_ms,
                error_code=ErrorCode.EXECUTION_CANCELLED,
            )
            raise
        except ToolBridgeError as error:
            return self._failure_response(
                error=error,
                tool_name=response_tool_name,
                correlation_id=response_correlation_id,
                started_at=started_at,
            )
        except Exception as error:
            normalized = ToolExecutionFailedError()
            return self._failure_response(
                error=normalized,
                tool_name=response_tool_name,
                correlation_id=response_correlation_id,
                started_at=started_at,
                exception_type=type(error).__name__,
            )

        duration_ms = self._duration_ms(started_at)
        self._event_logger.succeeded(
            tool_name=request.tool_name,
            correlation_id=request.correlation_id,
            duration_ms=duration_ms,
        )
        return ToolExecutionResponse(
            tool_name=request.tool_name,
            correlation_id=request.correlation_id,
            success=True,
            duration_ms=duration_ms,
            result=result,
        )

    async def _invoke(self, handler: ToolHandler, arguments: ToolInput) -> object:
        """Invoke async handlers directly and isolate sync handlers in a thread."""

        if inspect.iscoroutinefunction(handler):
            awaitable = handler(arguments)
            return await cast(Any, awaitable)

        result = await asyncio.to_thread(handler, arguments)
        if inspect.isawaitable(result):
            return await cast(Any, result)
        return result

    def _failure_response(
        self,
        *,
        error: ToolBridgeError,
        tool_name: str | None,
        correlation_id: str,
        started_at: float,
        exception_type: str | None = None,
    ) -> ToolExecutionResponse:
        """Build and log a normalized failure response."""

        duration_ms = self._duration_ms(started_at)
        self._event_logger.failed(
            tool_name=tool_name,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            error_code=error.code,
            exception_type=exception_type,
        )
        return ToolExecutionResponse(
            tool_name=tool_name,
            correlation_id=correlation_id,
            success=False,
            duration_ms=duration_ms,
            error=ToolErrorDetail(
                code=error.code,
                message=error.message,
                retryable=error.retryable,
                correlation_id=correlation_id,
                details=error.details,
            ),
        )

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1000, 3)

    @staticmethod
    def _safe_tool_name(tool_name: object) -> str | None:
        if isinstance(tool_name, str) and TOOL_NAME_PATTERN.fullmatch(tool_name):
            return tool_name
        return None

    @staticmethod
    def _safe_correlation_id(correlation_id: object, *, fallback: str) -> str:
        if isinstance(correlation_id, str) and fullmatch(CORRELATION_ID_PATTERN, correlation_id):
            return correlation_id
        return fallback

