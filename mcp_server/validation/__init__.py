"""Validation utilities for MCP server.

Provides request, response, and tool schema validation.
"""

import json
import logging
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base validation error."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class RequestValidator:
    """Validates incoming JSON-RPC requests."""

    # JSON-RPC 2.0 request schema
    REQUEST_SCHEMA = {
        "type": "object",
        "required": ["jsonrpc", "method"],
        "properties": {
            "jsonrpc": {"const": "2.0"},
            "method": {"type": "string", "minLength": 1},
            "params": {"type": ["object", "array", "null"]},
            "id": {"type": ["string", "number", "null"]},
        },
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        """Initialize validator."""
        self._validator = Draft202012Validator(self.REQUEST_SCHEMA)

    def validate(self, request: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a JSON-RPC request.

        Args:
            request: Request dictionary.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if not isinstance(request, dict):
            return False, ["Request must be a JSON object"]

        errors = list(self._validator.iter_errors(request))
        if errors:
            return False, [f"{e.json_path}: {e.message}" for e in errors]

        return True, []

    def validate_initialize(self, params: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate initialize request params.

        Args:
            params: Initialize params.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if not isinstance(params, dict):
            return False, ["Initialize params must be an object"]

        # Check required fields
        if "protocolVersion" not in params:
            return False, ["Missing required field: protocolVersion"]

        if "capabilities" not in params:
            return False, ["Missing required field: capabilities"]

        if "clientInfo" not in params:
            return False, ["Missing required field: clientInfo"]

        return True, []

    def validate_tools_call(self, params: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate tools/call request params.

        Args:
            params: Call params.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if not isinstance(params, dict):
            return False, ["Params must be an object"]

        if "name" not in params:
            return False, ["Missing required field: name"]

        if not isinstance(params["name"], str):
            return False, ["Field 'name' must be a string"]

        if "arguments" in params and not isinstance(params["arguments"], dict):
            return False, ["Field 'arguments' must be an object"]

        return True, []

    def validate_tools_list(self, params: dict[str, Any] | None) -> tuple[bool, list[str]]:
        """Validate tools/list request params.

        Args:
            params: List params (can be None/empty).

        Returns:
            Tuple of (is_valid, error_messages).
        """
        # tools/list has optional params
        if params is not None and not isinstance(params, dict):
            return False, ["Params must be an object or null"]
        return True, []


class ResponseValidator:
    """Validates outgoing JSON-RPC responses."""

    # JSON-RPC 2.0 response schema
    RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["jsonrpc", "id"],
        "properties": {
            "jsonrpc": {"const": "2.0"},
            "result": {},
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "integer"},
                    "message": {"type": "string"},
                    "data": {},
                },
            },
            "id": {"type": ["string", "number", "null"]},
        },
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        """Initialize validator."""
        self._validator = Draft202012Validator(self.RESPONSE_SCHEMA)

    def validate(self, response: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a JSON-RPC response.

        Args:
            response: Response dictionary.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if not isinstance(response, dict):
            return False, ["Response must be a JSON object"]

        # Check exactly one of result or error
        has_result = "result" in response
        has_error = "error" in response
        if has_result == has_error:  # Both or neither
            return False, ["Response must have exactly one of 'result' or 'error'"]

        errors = list(self._validator.iter_errors(response))
        if errors:
            return False, [f"{e.json_path}: {e.message}" for e in errors]

        return True, []

    def build_success_response(self, id_: Any, result: Any) -> dict[str, Any]:
        """Build a valid success response.

        Args:
            id_: Request ID.
            result: Result value.

        Returns:
            Valid JSON-RPC response.
        """
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": id_,
        }

    def build_error_response(
        self,
        id_: Any,
        code: int,
        message: str,
        data: Any = None,
    ) -> dict[str, Any]:
        """Build a valid error response.

        Args:
            id_: Request ID.
            code: Error code.
            message: Error message.
            data: Optional error data.

        Returns:
            Valid JSON-RPC error response.
        """
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {
            "jsonrpc": "2.0",
            "error": error,
            "id": id_,
        }


class ToolSchemaValidator:
    """Validates tool input/output schemas."""

    def __init__(self) -> None:
        """Initialize validator."""
        pass

    def validate_input_schema(self, schema: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a tool input schema.

        Args:
            schema: JSON Schema for tool input.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        if not isinstance(schema, dict):
            return False, ["Input schema must be a dictionary"]

        if schema.get("type") != "object":
            errors.append("Input schema type must be 'object'")

        if "properties" in schema and not isinstance(schema["properties"], dict):
            errors.append("Properties must be a dictionary")

        # Try to compile schema
        try:
            Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            errors.append(f"Invalid JSON Schema: {e.message}")

        return len(errors) == 0, errors

    def validate_output_schema(self, schema: dict[str, Any] | None) -> tuple[bool, list[str]]:
        """Validate a tool output schema.

        Args:
            schema: JSON Schema for tool output (can be None).

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if schema is None:
            return True, []

        return self.validate_input_schema(schema)

    def validate_arguments(
        self,
        arguments: dict[str, Any],
        schema: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate arguments against a schema.

        Args:
            arguments: Input arguments.
            schema: JSON Schema to validate against.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if not isinstance(arguments, dict):
            return False, ["Arguments must be a dictionary"]

        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(arguments))
            if errors:
                return False, [f"{e.json_path}: {e.message}" for e in errors]
        except jsonschema.SchemaError as e:
            return False, [f"Invalid schema: {e.message}"]

        return True, []

    def validate_result(
        self,
        result: Any,
        schema: dict[str, Any] | None,
    ) -> tuple[bool, list[str]]:
        """Validate tool result against output schema.

        Args:
            result: Tool result.
            schema: Output schema (can be None).

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if schema is None:
            return True, []

        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(result))
            if errors:
                return False, [f"{e.json_path}: {e.message}" for e in errors]
        except jsonschema.SchemaError as e:
            return False, [f"Invalid output schema: {e.message}"]

        return True, []


# Module-level instances for convenience
request_validator = RequestValidator()
response_validator = ResponseValidator()
tool_schema_validator = ToolSchemaValidator()


class ToolSchemaValidator:
    """Validates tool input/output schemas."""

    def __init__(self) -> None:
        """Initialize validator."""
        pass

    def validate_input_schema(self, schema: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a tool input schema.

        Args:
            schema: JSON Schema for tool input.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        if not isinstance(schema, dict):
            return False, ["Input schema must be a dictionary"]

        if schema.get("type") != "object":
            errors.append("Input schema type must be 'object'")

        if "properties" in schema and not isinstance(schema["properties"], dict):
            errors.append("Properties must be a dictionary")

        # Try to compile schema
        try:
            Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            errors.append(f"Invalid JSON Schema: {e.message}")

        return len(errors) == 0, errors

    def validate_output_schema(self, schema: dict[str, Any] | None) -> tuple[bool, list[str]]:
        """Validate a tool output schema.

        Args:
            schema: JSON Schema for tool output (can be None).

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if schema is None:
            return True, []

        return self.validate_input_schema(schema)

    def validate_arguments(
        self,
        arguments: dict[str, Any],
        schema: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate arguments against a schema.

        Args:
            arguments: Input arguments.
            schema: JSON Schema to validate against.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if not isinstance(arguments, dict):
            return False, ["Arguments must be a dictionary"]

        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(arguments))
            if errors:
                return False, [f"{e.json_path}: {e.message}" for e in errors]
        except jsonschema.SchemaError as e:
            return False, [f"Invalid schema: {e.message}"]

        return True, []

    def validate_result(
        self,
        result: Any,
        schema: dict[str, Any] | None,
    ) -> tuple[bool, list[str]]:
        """Validate tool result against output schema.

        Args:
            result: Tool result.
            schema: Output schema (can be None).

        Returns:
            Tuple of (is_valid, error_messages).
        """
        if schema is None:
            return True, []

        try:
            validator = Draft202012Validator(schema)
            errors = list(validator.iter_errors(result))
            if errors:
                return False, [f"{e.json_path}: {e.message}" for e in errors]
        except jsonschema.SchemaError as e:
            return False, [f"Invalid output schema: {e.message}"]

        return True, []

    def validate_tool_schemas(self, tool: Any) -> list[str]:
        """Validate all schemas for a tool.

        Args:
            tool: Tool instance with get_input_schema and get_output_schema methods.

        Returns:
            List of error messages (empty if all valid).
        """
        errors = []

        input_schema = tool.get_input_schema()
        is_valid, errors_list = self.validate_input_schema(input_schema)
        if not is_valid:
            errors.extend([f"Input schema: {e}" for e in errors_list])

        output_schema = tool.get_output_schema()
        if output_schema is not None:
            is_valid, errors_list = self.validate_output_schema(output_schema)
            if not is_valid:
                errors.extend([f"Output schema: {e}" for e in errors_list])

        return errors


# Module-level instances for convenience
request_validator = RequestValidator()
response_validator = ResponseValidator()
tool_schema_validator = ToolSchemaValidator()