"""Security tests for structured provider logging."""

import json
import logging

from toolbridge.providers.infrastructure.logging import ProviderJsonFormatter


def test_provider_formatter_emits_only_allowlisted_metadata() -> None:
    record = logging.LogRecord(
        name="toolbridge.providers",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="secret-message-that-must-not-be-emitted",
        args=(),
        exc_info=None,
    )
    record.provider = "cerebras"
    record.latency_ms = 12.5
    record.status = "degraded"
    record.request_id = "request-1"
    record.error_category = "rate_limit"
    record.api_key = "secret-api-key"
    record.prompt = "private prompt"
    record.response = "private response"

    output = ProviderJsonFormatter().format(record)
    payload = json.loads(output)

    assert payload["provider"] == "cerebras"
    assert payload["latency_ms"] == 12.5
    assert payload["status"] == "degraded"
    assert payload["request_id"] == "request-1"
    assert payload["error_category"] == "rate_limit"
    assert "api_key" not in payload
    assert "prompt" not in payload
    assert "response" not in payload
    assert "secret-api-key" not in output
    assert "private prompt" not in output
    assert "private response" not in output
    assert "secret-message-that-must-not-be-emitted" not in output
