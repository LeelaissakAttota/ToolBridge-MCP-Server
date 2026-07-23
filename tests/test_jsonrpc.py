"""Tests for JSON-RPC functionality."""

from mcp_server.validation import (
    RequestValidator,
    ResponseValidator,
)
from mcp_server.exceptions.mcp import (
    InvalidRequest,
    MethodNotFound,
    InvalidParams,
    InternalError,
    ToolNotFound,
    ToolExecutionError,
    MCPError,
    create_mcp_error,
    ERROR_CODE_MAP,
)


class TestJSONRPCRequestValidation:
    """Tests for JSON-RPC request validation."""

    def test_valid_request(self):
        """Test valid JSON-RPC 2.0 request."""
        request = {"jsonrpc": "2.0", "method": "test", "id": 1}
        is_valid, errors = RequestValidator().validate(request)
        assert is_valid is True

    def test_valid_notification(self):
        """Test valid notification (no id)."""
        request = {"jsonrpc": "2.0", "method": "notify"}
        is_valid, errors = RequestValidator().validate(request)
        assert is_valid is True

    def test_invalid_not_object(self):
        """Test non-object request fails."""
        is_valid, errors = RequestValidator().validate("not an object")
        assert is_valid is False

    def test_missing_jsonrpc(self):
        """Test missing jsonrpc field."""
        request = {"method": "test", "id": 1}
        is_valid, errors = RequestValidator().validate(request)
        assert is_valid is False

    def test_wrong_jsonrpc_version(self):
        """Test wrong JSON-RPC version."""
        request = {"jsonrpc": "1.0", "method": "test", "id": 1}
        is_valid, errors = RequestValidator().validate(request)
        assert is_valid is False

    def test_missing_method(self):
        """Test missing method field."""
        request = {"jsonrpc": "2.0", "id": 1}
        is_valid, errors = RequestValidator().validate(request)
        assert is_valid is False


class TestJSONRPCResponseValidation:
    """Tests for JSON-RPC response validation."""

    def test_valid_success_response(self):
        """Test valid success response."""
        response = {"jsonrpc": "2.0", "result": {}, "id": 1}
        is_valid, errors = ResponseValidator().validate(response)
        assert is_valid is True

    def test_valid_error_response(self):
        """Test valid error response."""
        response = {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Error"}, "id": 1}
        is_valid, errors = ResponseValidator().validate(response)
        assert is_valid is True

    def test_both_result_and_error(self):
        """Test response with both result and error fails."""
        response = {"jsonrpc": "2.0", "result": {}, "error": {"code": -32600, "message": "Err"}, "id": 1}
        is_valid, errors = ResponseValidator().validate(response)
        assert is_valid is False

    def test_neither_result_nor_error(self):
        """Test response with neither result nor error fails."""
        response = {"jsonrpc": "2.0", "id": 1}
        is_valid, errors = ResponseValidator().validate(response)
        assert is_valid is False

    def test_invalid_error_object(self):
        """Test invalid error object."""
        response = {"jsonrpc": "2.0", "error": {"message": "Missing code"}, "id": 1}
        is_valid, errors = ResponseValidator().validate(response)
        assert is_valid is False

    def test_build_success_response(self):
        """Test building success response."""
        resp = ResponseValidator().build_success_response("test-id", {"data": "value"})
        assert resp["jsonrpc"] == "2.0"
        assert resp["result"] == {"data": "value"}
        assert resp["id"] == "test-id"

    def test_build_error_response(self):
        """Test building error response."""
        resp = ResponseValidator().build_error_response("test-id", -32601, "Not found", {"method": "test"})
        assert resp["jsonrpc"] == "2.0"
        assert resp["error"]["code"] == -32601
        assert resp["error"]["message"] == "Not found"
        assert resp["error"]["data"] == {"method": "test"}
        assert resp["id"] == "test-id"


class TestMCPExceptions:
    """Tests for MCP exception classes."""

    def test_invalid_request_error(self):
        """Test InvalidRequest exception."""
        err = InvalidRequest("Bad request")
        assert err.code == -32600
        assert err.message == "Bad request"

    def test_method_not_found_error(self):
        """Test MethodNotFound exception."""
        err = MethodNotFound("unknown_method")
        assert err.code == -32601
        assert "unknown_method" in err.message

    def test_invalid_params_error(self):
        """Test InvalidParams exception."""
        err = InvalidParams("Invalid params", data={"field": "name"})
        assert err.code == -32602
        assert err.data == {"field": "name"}

    def test_internal_error(self):
        """Test InternalError exception."""
        err = InternalError("Internal error")
        assert err.code == -32603

    def test_tool_not_found_error(self):
        """Test ToolNotFound exception."""
        err = ToolNotFound("my_tool")
        assert err.code == -32001
        assert "my_tool" in err.message

    def test_tool_execution_error(self):
        """Test ToolExecutionError exception."""
        err = ToolExecutionError("Execution failed", data={"tool": "test"})
        assert err.code == -32002
        assert err.data == {"tool": "test"}

    def test_to_json_rpc_error(self):
        """Test to_json_rpc_error method."""
        err = InvalidParams("Bad params", data={"field": "name"})
        json_err = err.to_json_rpc_error()
        assert json_err["code"] == -32602
        assert json_err["message"] == "Bad params"
        assert json_err["data"] == {"field": "name"}

    def test_create_mcp_error_known_code(self):
        """Test create_mcp_error with known code."""
        err = create_mcp_error(-32601, "Method not found")
        assert isinstance(err, MethodNotFound)

    def test_create_mcp_error_unknown_code(self):
        """Test create_mcp_error with unknown code."""
        err = create_mcp_error(-99999, "Unknown error")
        assert isinstance(err, MCPError)
        assert err.code == -99999

    def test_error_code_map(self):
        """Test ERROR_CODE_MAP has expected codes."""
        assert -32700 in ERROR_CODE_MAP  # ParseError
        assert -32600 in ERROR_CODE_MAP  # InvalidRequest
        assert -32601 in ERROR_CODE_MAP  # MethodNotFound
        assert -32602 in ERROR_CODE_MAP  # InvalidParams
        assert -32603 in ERROR_CODE_MAP  # InternalError
        assert -32001 in ERROR_CODE_MAP  # ToolNotFound
        assert -32002 in ERROR_CODE_MAP  # ToolExecutionError


class TestErrorResponseBuilding:
    """Tests for building error responses."""

    def test_method_not_found_response(self):
        """Test building MethodNotFound response."""
        err = MethodNotFound("test_method")
        resp = ResponseValidator().build_error_response(1, err.code, err.message, err.data)
        assert resp["error"]["code"] == -32601
        assert "test_method" in resp["error"]["message"]

    def test_invalid_params_response(self):
        """Test building InvalidParams response."""
        err = InvalidParams("Invalid param", data={"param": "name"})
        resp = ResponseValidator().build_error_response(1, err.code, err.message, err.data)
        assert resp["error"]["code"] == -32602
        assert resp["error"]["data"]["param"] == "name"

    def test_tool_not_found_response(self):
        """Test building ToolNotFound response."""
        err = ToolNotFound("my_tool")
        resp = ResponseValidator().build_error_response(1, err.code, err.message, err.data)
        assert resp["error"]["code"] == -32001
        assert resp["error"]["data"]["tool_name"] == "my_tool"