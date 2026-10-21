"""Optional MCP bearer-token and allowed-host protection."""

from collections.abc import Iterator

import pytest
from asgi_client import ASGITestClient as TestClient
from mcp.server.fastmcp import FastMCP

from toolbridge.adapters.mcp_security import (
    BearerTokenMiddleware,
    build_transport_security,
    parse_csv_setting,
)
from toolbridge.config import Settings

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "tests", "version": "1"},
    },
}
HEADERS = {"accept": "application/json, text/event-stream"}


def _client(token: str | None = None, hosts: str = "", origins: str = "") -> TestClient:
    mcp = FastMCP(
        "security-test",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        transport_security=build_transport_security(hosts, origins),
    )
    inner = mcp.streamable_http_app()
    app = inner if token is None else BearerTokenMiddleware(inner, token)
    return TestClient(app, base_url="http://127.0.0.1:8000", lifespan_app=inner)


@pytest.fixture
def secured() -> Iterator[TestClient]:
    with _client(token="s3cret") as client:
        yield client


def test_default_settings_keep_auth_and_hosts_unchanged() -> None:
    settings = Settings(_env_file=None)

    assert settings.mcp_auth_token_value is None
    assert build_transport_security(settings.mcp_allowed_hosts, "") is None


def test_unset_token_allows_requests() -> None:
    with _client() as client:
        assert client.post("/", json=INITIALIZE, headers=HEADERS).status_code == 200


@pytest.mark.parametrize("authorization", [None, "Bearer wrong", "s3cret", "Basic czNjcmV0"])
def test_token_rejects_missing_or_wrong_credentials(
    secured: TestClient, authorization: str | None
) -> None:
    headers = dict(HEADERS)
    if authorization is not None:
        headers["authorization"] = authorization

    response = secured.post("/", json=INITIALIZE, headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    assert "s3cret" not in response.text


def test_token_accepts_valid_bearer(secured: TestClient) -> None:
    headers = {**HEADERS, "authorization": "Bearer s3cret"}

    assert secured.post("/", json=INITIALIZE, headers=headers).status_code == 200


def test_allowed_hosts_extend_loopback_defaults() -> None:
    with _client(hosts="tools.example.com") as client:
        proxied = client.post(
            "/", json=INITIALIZE, headers={**HEADERS, "host": "tools.example.com"}
        )
        local = client.post("/", json=INITIALIZE, headers=HEADERS)
        other = client.post("/", json=INITIALIZE, headers={**HEADERS, "host": "evil.example"})

    assert proxied.status_code == 200
    assert local.status_code == 200
    assert other.status_code == 421


def test_parse_csv_setting_trims_and_dedupes() -> None:
    assert parse_csv_setting(" a.example , ,b.example,a.example ") == ("a.example", "b.example")


def test_empty_token_is_rejected_by_middleware() -> None:
    with pytest.raises(ValueError):
        BearerTokenMiddleware(lambda *_: None, "")  # type: ignore[arg-type]
