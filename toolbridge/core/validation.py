"""Request, input, and response validation for MCP tool execution."""

import json
from typing import Any

from pydantic import ValidationError

from toolbridge.core.contracts import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolInput,
)
from toolbridge.core.errors import RequestValidationError, ResponseValidationError


def _validation_details(error: ValidationError) -> dict[str, Any]:
    """Return safe validation metadata without rejected values."""

    fields = sorted(
        {
            ".".join(str(part) for part in issue["loc"])
            for issue in error.errors(include_input=False, include_url=False)
        }
    )
    return {"fields": fields, "issue_count": error.error_count()}


def _json_size(value: object) -> int:
    """Return the encoded JSON size or raise a safe request error."""

    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise RequestValidationError("The request must contain valid JSON values.") from error
    return len(encoded)


class RequestValidator:
    """Validate execution requests and tool-specific arguments."""

    def __init__(self, max_request_bytes: int) -> None:
        if max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be greater than zero")
        self._max_request_bytes = max_request_bytes

    def validate_request(
        self,
        *,
        tool_name: object,
        arguments: object,
        correlation_id: object,
    ) -> ToolExecutionRequest:
        """Validate the common execution request contract and size limit."""

        payload = {
            "tool_name": tool_name,
            "arguments": arguments,
            "correlation_id": correlation_id,
        }
        if _json_size(payload) > self._max_request_bytes:
            raise RequestValidationError(
                "The request exceeds the configured size limit.",
                details={"max_request_bytes": self._max_request_bytes},
            )
        try:
            return ToolExecutionRequest.model_validate(payload, strict=True)
        except ValidationError as error:
            raise RequestValidationError(
                "The request does not match the execution contract.",
                details=_validation_details(error),
            ) from error

    def validate_arguments(
        self,
        definition: ToolDefinition,
        arguments: dict[str, Any],
    ) -> ToolInput:
        """Validate arguments against the selected tool contract."""

        try:
            return definition.input_model.model_validate(arguments, strict=True)
        except ValidationError as error:
            raise RequestValidationError(
                "The tool arguments do not match the declared input schema.",
                details=_validation_details(error),
            ) from error


class ResponseValidator:
    """Validate and bound structured tool output."""

    def __init__(self, max_response_bytes: int) -> None:
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be greater than zero")
        self._max_response_bytes = max_response_bytes

    def validate(
        self,
        definition: ToolDefinition,
        result: object,
    ) -> dict[str, Any]:
        """Return JSON-compatible output or raise a normalized error."""

        try:
            validated = definition.output_model.model_validate(result, strict=True)
        except ValidationError as error:
            raise ResponseValidationError(
                "The tool returned data that violates its output schema.",
                details=_validation_details(error),
            ) from error

        output = validated.model_dump(mode="json")
        try:
            output_size = _json_size(output)
        except RequestValidationError as error:
            raise ResponseValidationError(
                "The tool returned data that cannot be encoded as JSON."
            ) from error
        if output_size > self._max_response_bytes:
            raise ResponseValidationError(
                "The tool response exceeds the configured size limit.",
                details={"max_response_bytes": self._max_response_bytes},
            )
        return output

