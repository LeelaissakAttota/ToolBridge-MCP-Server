"""Tests for validation module."""

import pytest
from mcp_server.validation import (
    RequestValidator,
    ResponseValidator,
    ToolSchemaValidator,
    ValidationError,
    request_validator,
    response_validator,
    tool_schema_validator,
)
from mcp_server.tools.base import BaseTool


class ValidTool(BaseTool):
    name = "valid_tool"
    description = "Valid tool"

    def get_input_schema(self):
        return {"type": "object", "properties": {}}

    async def execute(self, arguments):
        return {}


class InvalidTool(BaseTool):
    name = "invalid_tool"
    description = "Invalid tool"

    def get_input_schema(self):
        return {"type": "array"}  # Wrong type

    async def execute(self, arguments):
        return {}


class TestRequestValidator:
    """Tests for RequestValidator."""

    def test_valid_request(self):
        """Test validating a valid JSON-RPC request."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        is_valid, errors = request_validator.validate(request)
        assert is_valid is True
        assert errors == []

    def test_valid_request_with_params(self):
        """Test request with params."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "test", "arguments": {}},
            "id": 2
        }
        is_valid, errors = request_validator.validate(request)
        assert is_valid is True

    def test_missing_jsonrpc(self):
        """Test request missing jsonrpc field."""
        request = {"method": "tools/list", "id": 1}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is False
        assert any("jsonrpc" in e for e in errors)

    def test_invalid_jsonrpc_version(self):
        """Test request with wrong JSON-RPC version."""
        request = {"jsonrpc": "1.0", "method": "tools/list", "id": 1}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is False
        assert any("2.0" in e for e in errors)

    def test_missing_method(self):
        """Test request missing method."""
        request = {"jsonrpc": "2.0", "id": 1}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is False
        assert any("method" in e for e in errors)

    def test_invalid_method_type(self):
        """Test method must be string."""
        request = {"jsonrpc": "2.0", "method": 123, "id": 1}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is False

    def test_invalid_params_type(self):
        """Test params must be object."""
        request = {"jsonrpc": "2.0", "method": "test", "params": "not-object", "id": 1}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is False

    def test_invalid_id_type(self):
        """Test id must be string, number, or null."""
        request = {"jsonrpc": "2.0", "method": "test", "id": []}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is False

    def test_notification_no_id(self):
        """Test notification (no id) is valid."""
        request = {"jsonrpc": "2.0", "method": "notifications/test"}
        is_valid, errors = request_validator.validate(request)
        assert is_valid is True

    def test_initialize_params(self):
        """Test validate_initialize_params."""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
        is_valid, errors = request_validator.validate_initialize(params)
        assert is_valid is True

    def test_initialize_missing_protocol_version(self):
        """Test initialize missing protocolVersion."""
        params = {"capabilities": {}, "clientInfo": {"name": "test"}}
        is_valid, errors = request_validator.validate_initialize(params)
        assert is_valid is False
        assert any("protocolVersion" in e for e in errors)

    def test_tools_call_params(self):
        """Test validate_tools_call_params."""
        params = {"name": "test_tool", "arguments": {"arg": "value"}}
        is_valid, errors = request_validator.validate_tools_call(params)
        assert is_valid is True

    def test_tools_call_missing_name(self):
        """Test tools/call missing name."""
        params = {"arguments": {}}
        is_valid, errors = request_validator.validate_tools_call(params)
        assert is_valid is False
        assert any("name" in e for e in errors)

    def test_tools_call_invalid_name_type(self):
        """Test tools/call name must be string."""
        params = {"name": 123, "arguments": {}}
        is_valid, errors = request_validator.validate_tools_call(params)
        assert is_valid is False

    def test_tools_list_params(self):
        """Test validate_tools_list_params."""
        is_valid, errors = request_validator.validate_tools_list(None)
        assert is_valid is True
        is_valid, errors = request_validator.validate_tools_list({})
        assert is_valid is True
        is_valid, errors = request_validator.validate_tools_list("not-object")
        assert is_valid is False


class TestResponseValidator:
    """Tests for ResponseValidator."""

    def test_valid_success_response(self):
        """Test valid success response."""
        response = {
            "jsonrpc": "2.0",
            "result": {"tools": []},
            "id": 1
        }
        is_valid, errors = response_validator.validate(response)
        assert is_valid is True

    def test_valid_error_response(self):
        """Test valid error response."""
        response = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": 1
        }
        is_valid, errors = response_validator.validate(response)
        assert is_valid is True

    def test_missing_jsonrpc(self):
        """Test response missing jsonrpc."""
        response = {"result": {}, "id": 1}
        is_valid, errors = response_validator.validate(response)
        assert is_valid is False

    def test_both_result_and_error(self):
        """Test response cannot have both result and error."""
        response = {
            "jsonrpc": "2.0",
            "result": {},
            "error": {"code": -32600, "message": "Error"},
            "id": 1
        }
        is_valid, errors = response_validator.validate(response)
        assert is_valid is False
        assert any("exactly one" in e.lower() or "one of" in e.lower() for e in errors)

    def test_neither_result_nor_error(self):
        """Test response must have result or error."""
        response = {"jsonrpc": "2.0", "id": 1}
        is_valid, errors = response_validator.validate(response)
        assert is_valid is False

    def test_invalid_error_object(self):
        """Test error object must have code and message."""
        response = {
            "jsonrpc": "2.0",
            "error": {"message": "Missing code"},
            "id": 1
        }
        is_valid, errors = response_validator.validate(response)
        assert is_valid is False

    def test_build_success_response(self):
        """Test build_success_response."""
        response = response_validator.build_success_response(1, {"data": "test"})
        assert response["jsonrpc"] == "2.0"
        assert response["result"] == {"data": "test"}
        assert response["id"] == 1

    def test_build_error_response(self):
        """Test build_error_response."""
        response = response_validator.build_error_response(1, -32601, "Not found", {"method": "test"})
        assert response["jsonrpc"] == "2.0"
        assert response["error"]["code"] == -32601
        assert response["error"]["message"] == "Not found"
        assert response["error"]["data"] == {"method": "test"}
        assert response["id"] == 1


class TestToolSchemaValidator:
    """Tests for ToolSchemaValidator."""

    def test_valid_input_schema(self):
        """Test valid tool input schema."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"]
        }
        is_valid, errors = tool_schema_validator.validate_input_schema(schema)
        assert is_valid is True

    def test_invalid_schema_not_object(self):
        """Test schema type must be object."""
        schema = {"type": "array", "items": {"type": "string"}}
        is_valid, errors = tool_schema_validator.validate_input_schema(schema)
        assert is_valid is False
        assert any("object" in e for e in errors)

    def test_invalid_schema_properties(self):
        """Test properties must be dict."""
        schema = {"type": "object", "properties": "not-dict"}
        is_valid, errors = tool_schema_validator.validate_input_schema(schema)
        assert is_valid is False

    def test_none_output_schema(self):
        """Test None output schema is valid."""
        is_valid, errors = tool_schema_validator.validate_output_schema(None)
        assert is_valid is True

    def test_validate_arguments_valid(self):
        """Test validating arguments against schema."""
        schema = {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"]
        }
        is_valid, errors = tool_schema_validator.validate_arguments({"value": 42}, schema)
        assert is_valid is True

    def test_validate_arguments_missing_required(self):
        """Test missing required field."""
        schema = {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"]
        }
        is_valid, errors = tool_schema_validator.validate_arguments({}, schema)
        assert is_valid is False
        assert any("required" in e for e in errors)

    def test_validate_arguments_wrong_type(self):
        """Test wrong type for field."""
        schema = {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
        }
        is_valid, errors = tool_schema_validator.validate_arguments({"value": "not-int"}, schema)
        assert is_valid is False

    def test_validate_result_valid(self):
        """Test validating result against output schema."""
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        is_valid, errors = tool_schema_validator.validate_result({"result": "ok"}, schema)
        assert is_valid is True

    def test_validate_result_none_schema(self):
        """Test None output schema passes validation."""
        is_valid, errors = tool_schema_validator.validate_result({"any": "value"}, None)
        assert is_valid is True

    def test_validate_tool_schemas_valid(self):
        """Test validating tool with valid schemas."""
        from mcp_server.tools.base import BaseTool

        class ValidTool(BaseTool):
            name = "valid"
            description = "Valid tool"

            def get_input_schema(self):
                return {"type": "object", "properties": {}}

            def get_output_schema(self):
                return {"type": "object", "properties": {}}

            async def execute(self, arguments):
                return {}

        tool = ValidTool()
        errors = tool_schema_validator.validate_tool_schemas(tool)
        assert errors == []

    def test_validate_tool_schemas_invalid(self):
        """Test validating tool with invalid schemas."""
        from mcp_server.tools.base import BaseTool

        class InvalidTool(BaseTool):
            name = "invalid"
            description = "Invalid tool"

            def get_input_schema(self):
                return {"type": "array"}  # Wrong type

            def get_output_schema(self):
                return {"type": "object", "properties": {}}

            async def execute(self, arguments):
                return {}


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_basic(self):
        """Test ValidationError creation."""
        error = ValidationError("Test error", ["error1", "error2"])
        assert str(error) == "Test error"
        assert error.errors == ["error1", "error2"]

    def test_validation_error_no_errors(self):
        """Test ValidationError without error list."""
        error = ValidationError("Test error")
        assert error.errors == []