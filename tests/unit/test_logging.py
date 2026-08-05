"""Unit tests for structured execution logging."""

import json
import logging

from toolbridge.adapters.logging import StructuredJsonFormatter


def test_formatter_emits_only_allowlisted_metadata() -> None:
    record = logging.LogRecord(
        name="toolbridge.execution",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="message-that-is-not-emitted",
        args=(),
        exc_info=None,
    )
    record.event = "tool_execution_succeeded"
    record.tool_name = "system_status"
    record.correlation_id = "correlation-1"
    record.duration_ms = 1.25
    record.arguments = {"token": "secret-value"}
    record.result = {"private": "secret-value"}

    output = StructuredJsonFormatter().format(record)
    payload = json.loads(output)

    assert payload["event"] == "tool_execution_succeeded"
    assert payload["tool_name"] == "system_status"
    assert payload["correlation_id"] == "correlation-1"
    assert "arguments" not in payload
    assert "result" not in payload
    assert "secret-value" not in output
    assert "message-that-is-not-emitted" not in output

