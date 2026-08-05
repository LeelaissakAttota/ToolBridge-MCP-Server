"""Unit tests for the MCP core execution boundary."""

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from toolbridge.core.contracts import (
    ErrorCode,
    ToolDefinition,
    ToolInput,
    ToolOutput,
)
from toolbridge.core.executor import ToolExecutor
from toolbridge.core.registry import ToolRegistry
from toolbridge.core.validation import RequestValidator, ResponseValidator


class ValueInput(ToolInput):
    """Integer input used by execution tests."""

    value: int


class ValueOutput(ToolOutput):
    """Integer output used by execution tests."""

    value: int


class RecordingLogger:
    """Capture safe execution events for assertions."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def started(self, *, tool_name: str, correlation_id: str) -> None:
        self.events.append(
            {"event": "started", "tool_name": tool_name, "correlation_id": correlation_id}
        )

    def succeeded(
        self,
        *,
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
    ) -> None:
        self.events.append(
            {
                "event": "succeeded",
                "tool_name": tool_name,
                "correlation_id": correlation_id,
                "duration_ms": duration_ms,
            }
        )

    def failed(
        self,
        *,
        tool_name: str | None,
        correlation_id: str,
        duration_ms: float,
        error_code: ErrorCode,
        exception_type: str | None = None,
    ) -> None:
        self.events.append(
            {
                "event": "failed",
                "tool_name": tool_name,
                "correlation_id": correlation_id,
                "duration_ms": duration_ms,
                "error_code": error_code,
                "exception_type": exception_type,
            }
        )


def build_executor(
    handler: Callable[[ValueInput], object],
    *,
    timeout_seconds: float = 1.0,
) -> tuple[ToolExecutor, RecordingLogger]:
    """Build an isolated executor with one registered test tool."""

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="value",
            description="Execute a value test.",
            input_model=ValueInput,
            output_model=ValueOutput,
            handler=handler,
            timeout_seconds=timeout_seconds,
        )
    )
    logger = RecordingLogger()
    executor = ToolExecutor(
        registry,
        RequestValidator(max_request_bytes=1_024),
        ResponseValidator(max_response_bytes=1_024),
        logger,
    )
    return executor, logger


def test_executor_runs_sync_handler_and_validates_response() -> None:
    executor, logger = build_executor(lambda data: ValueOutput(value=data.value + 1))

    response = asyncio.run(
        executor.execute("value", {"value": 4}, correlation_id="correlation-1")
    )

    assert response.success is True
    assert response.result == {"value": 5}
    assert [event["event"] for event in logger.events] == ["started", "succeeded"]
    assert all("arguments" not in event for event in logger.events)


def test_executor_rejects_unknown_tool() -> None:
    executor, _ = build_executor(lambda data: ValueOutput(value=data.value))

    response = asyncio.run(executor.execute("missing", {}))

    assert response.success is False
    assert response.error is not None
    assert response.error.code is ErrorCode.TOOL_NOT_FOUND
    assert response.error.message == "The requested tool is not available."


def test_executor_rejects_invalid_arguments() -> None:
    executor, _ = build_executor(lambda data: ValueOutput(value=data.value))

    response = asyncio.run(executor.execute("value", {"value": "4", "extra": True}))

    assert response.success is False
    assert response.error is not None
    assert response.error.code is ErrorCode.INVALID_REQUEST
    assert response.error.details["fields"] == ["extra", "value"]


def test_executor_normalizes_timeout() -> None:
    async def slow_handler(_: ValueInput) -> ValueOutput:
        await asyncio.sleep(1)
        return ValueOutput(value=1)

    executor, _ = build_executor(slow_handler, timeout_seconds=0.01)

    response = asyncio.run(executor.execute("value", {"value": 1}))

    assert response.success is False
    assert response.error is not None
    assert response.error.code is ErrorCode.EXECUTION_TIMEOUT
    assert response.error.retryable is True


def test_executor_hides_internal_exception_message() -> None:
    def failing_handler(_: ValueInput) -> ValueOutput:
        raise RuntimeError("secret-api-key-must-not-leak")

    executor, logger = build_executor(failing_handler)

    response = asyncio.run(executor.execute("value", {"value": 1}))
    serialized = response.model_dump_json()

    assert response.error is not None
    assert response.error.code is ErrorCode.EXECUTION_FAILED
    assert "secret-api-key-must-not-leak" not in serialized
    assert logger.events[-1]["exception_type"] == "RuntimeError"


def test_executor_rejects_invalid_response() -> None:
    executor, _ = build_executor(lambda _: {"wrong": 1})

    response = asyncio.run(executor.execute("value", {"value": 1}))

    assert response.error is not None
    assert response.error.code is ErrorCode.INVALID_RESPONSE


def test_executor_propagates_cancellation_and_logs_it() -> None:
    handler_started = asyncio.Event()

    async def cancellable_handler(_: ValueInput) -> ValueOutput:
        handler_started.set()
        await asyncio.sleep(10)
        return ValueOutput(value=1)

    executor, logger = build_executor(cancellable_handler)

    async def cancel_execution() -> None:
        task = asyncio.create_task(executor.execute("value", {"value": 1}))
        await handler_started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_execution())

    assert logger.events[-1]["error_code"] is ErrorCode.EXECUTION_CANCELLED

