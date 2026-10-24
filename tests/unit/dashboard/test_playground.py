"""Tests for the Tool Playground helpers (no Streamlit rendering)."""

from __future__ import annotations

import json

import httpx
import pytest

from toolbridge.dashboard import playground


def test_parse_body_accepts_json_and_sse() -> None:
    assert playground._parse_body('{"a": 1}') == {"a": 1}
    sse = 'event: message\ndata: {"result": {"ok": true}}\n\n'
    assert playground._parse_body(sse) == {"result": {"ok": True}}


def test_headers_add_bearer_only_when_token_set(monkeypatch) -> None:
    monkeypatch.setattr(playground, "_auth_token", lambda: None)
    assert "Authorization" not in playground._headers()
    monkeypatch.setattr(playground, "_auth_token", lambda: "t0k")
    assert playground._headers()["Authorization"] == "Bearer t0k"


class _FakeClient:
    def __init__(self, response: httpx.Response, sent: list) -> None:
        self.response, self.sent = response, sent

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None

    def post(self, url, headers, json):  # noqa: A002 - mirrors httpx signature
        self.sent.append((url, json))
        return self.response


def _patch_client(monkeypatch, response: httpx.Response) -> list:
    sent: list = []
    monkeypatch.setattr(playground, "_mcp_url", lambda: "http://127.0.0.1:1/mcp/")
    monkeypatch.setattr(playground, "_auth_token", lambda: None)
    monkeypatch.setattr(playground.httpx, "Client", lambda **_: _FakeClient(response, sent))
    return sent


def test_mcp_request_posts_json_rpc(monkeypatch) -> None:
    request = httpx.Request("POST", "http://127.0.0.1:1/mcp/")
    sent = _patch_client(
        monkeypatch, httpx.Response(200, text='{"result": {"tools": []}}', request=request)
    )
    assert playground.mcp_request("tools/list", {}) == {"result": {"tools": []}}
    url, payload = sent[0]
    assert url.endswith("/mcp/")
    assert payload["jsonrpc"] == "2.0" and payload["method"] == "tools/list"


def test_mcp_request_explains_401(monkeypatch) -> None:
    request = httpx.Request("POST", "http://127.0.0.1:1/mcp/")
    _patch_client(monkeypatch, httpx.Response(401, text="", request=request))
    with pytest.raises(RuntimeError, match="Unauthorized"):
        playground.mcp_request("tools/list", {})


def test_load_examples_reads_only_tool_calls(monkeypatch, tmp_path) -> None:
    (tmp_path / "03_system_status.json").write_text(
        json.dumps({"method": "tools/call", "params": {"name": "system_status", "arguments": {}}})
    )
    (tmp_path / "01_initialize.json").write_text(json.dumps({"method": "initialize"}))
    (tmp_path / "02_broken.json").write_text("{not json")
    (tmp_path / "E01_error.json").write_text(
        json.dumps({"method": "tools/call", "params": {"name": "x"}})
    )
    monkeypatch.setattr(playground, "REQUESTS_DIR", tmp_path)
    assert playground.load_examples() == {"system_status": [("System status", {})]}


def test_bundled_examples_cover_every_demo_tool() -> None:
    names = set(playground.load_examples())
    assert {"system_status", "csv_analysis", "sql_query", "currency_converter"} <= names


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"type": "string"}, "string"),
        ({"type": "integer"}, "integer"),
        ({"enum": ["a", "b"]}, "enum"),
        ({"anyOf": [{"type": "string", "enum": ["x"]}, {"type": "null"}]}, "enum"),
        ({"anyOf": [{"type": "number"}, {"type": "null"}]}, "number"),
        ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "json"),
        ({}, "json"),
    ],
)
def test_field_type(spec, expected) -> None:
    assert playground._field_type(spec) == expected


def test_env_helpers_write_and_detect_keys(monkeypatch, tmp_path) -> None:
    env = tmp_path / ".env"
    env.write_text("# TOOLBRIDGE_X__API_KEY=old\nTOOLBRIDGE_X__API_KEY=\n", encoding="utf-8")
    monkeypatch.setattr(playground, "ENV_PATH", env)
    monkeypatch.delenv("TOOLBRIDGE_X__API_KEY", raising=False)
    assert playground.env_var_is_set("TOOLBRIDGE_X__API_KEY") is False

    playground.write_env_var("TOOLBRIDGE_X__API_KEY", "secret-value")
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#")  # comments untouched
    assert lines[1] == "TOOLBRIDGE_X__API_KEY=secret-value"
    assert playground.env_var_is_set("TOOLBRIDGE_X__API_KEY") is True

    playground.write_env_var("TOOLBRIDGE_NEW", "1")
    assert env.read_text(encoding="utf-8").endswith("TOOLBRIDGE_NEW=1\n")


@pytest.mark.parametrize(("var", "value"), [("bad-name", "x"), ("GOOD", "a\nb")])
def test_write_env_var_rejects_unsafe_input(monkeypatch, tmp_path, var, value) -> None:
    monkeypatch.setattr(playground, "ENV_PATH", tmp_path / ".env")
    with pytest.raises(ValueError):
        playground.write_env_var(var, value)
