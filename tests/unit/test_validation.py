"""Unit tests for request, argument, and response validation."""

import pytest

from toolbridge.core.contracts import ToolDefinition, ToolInput, ToolOutput
from toolbridge.core.errors import RequestValidationError, ResponseValidationError
from toolbridge.core.validation import RequestValidator, ResponseValidator


class TextInput(ToolInput):
    """Strict text input used by validation tests."""

    text: str


class CountOutput(ToolOutput):
    """Strict numeric output used by validation tests."""

    count: int


def count_text(arguments: TextInput) -> CountOutput:
    """Return the length of a validated string."""

    return CountOutput(count=len(arguments.text))


DEFINITION = ToolDefinition(
    name="count_text",
    description="Count characters in test text.",
    input_model=TextInput,
    output_model=CountOutput,
    handler=count_text,
    timeout_seconds=1.0,
)


def test_request_validator_accepts_valid_request() -> None:
    validator = RequestValidator(max_request_bytes=1_024)

    request = validator.validate_request(
        tool_name="count_text",
        arguments={"text": "hello"},
        correlation_id="request-123",
    )

    assert request.arguments == {"text": "hello"}
    assert request.correlation_id == "request-123"


def test_request_validator_rejects_oversized_request() -> None:
    validator = RequestValidator(max_request_bytes=100)

    with pytest.raises(RequestValidationError) as caught:
        validator.validate_request(
            tool_name="count_text",
            arguments={"text": "x" * 200},
            correlation_id="request-123",
        )

    assert caught.value.details == {"max_request_bytes": 100}


def test_request_validator_rejects_non_json_values() -> None:
    validator = RequestValidator(max_request_bytes=1_024)

    with pytest.raises(RequestValidationError, match="valid JSON"):
        validator.validate_request(
            tool_name="count_text",
            arguments={"text": object()},
            correlation_id="request-123",
        )


def test_argument_validator_rejects_unknown_fields_without_values() -> None:
    validator = RequestValidator(max_request_bytes=1_024)

    with pytest.raises(RequestValidationError) as caught:
        validator.validate_arguments(
            DEFINITION,
            {"text": "safe", "secret": "must-not-appear"},
        )

    assert caught.value.details == {"fields": ["secret"], "issue_count": 1}
    assert "must-not-appear" not in str(caught.value.details)


def test_response_validator_accepts_declared_output() -> None:
    validator = ResponseValidator(max_response_bytes=1_024)

    result = validator.validate(DEFINITION, CountOutput(count=5))

    assert result == {"count": 5}


def test_response_validator_rejects_wrong_output_shape() -> None:
    validator = ResponseValidator(max_response_bytes=1_024)

    with pytest.raises(ResponseValidationError) as caught:
        validator.validate(DEFINITION, {"unexpected": 5})

    assert caught.value.details["fields"] == ["count", "unexpected"]


def test_response_validator_enforces_size_limit() -> None:
    class LargeOutput(ToolOutput):
        text: str

    large_definition = ToolDefinition(
        name="large",
        description="Return oversized test output.",
        input_model=TextInput,
        output_model=LargeOutput,
        handler=lambda _: LargeOutput(text="x" * 100),
        timeout_seconds=1.0,
    )
    validator = ResponseValidator(max_response_bytes=50)

    with pytest.raises(ResponseValidationError) as caught:
        validator.validate(large_definition, LargeOutput(text="x" * 100))

    assert caught.value.details == {"max_response_bytes": 50}
