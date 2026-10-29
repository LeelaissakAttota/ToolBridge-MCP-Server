"""Smoke tests for the ToolBridge ASGI application."""

from collections.abc import Iterator

import pytest
from asgi_client import ASGITestClient as TestClient
from mcp.types import LATEST_PROTOCOL_VERSION

from toolbridge.config import get_settings
from toolbridge.main import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Run one application lifespan for all endpoint smoke tests."""

    with TestClient(app, base_url="http://127.0.0.1:8000") as test_client:
        yield test_client


def test_service_info(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == "1.1.0"
    assert response.json()["status"] == "running"
    assert response.json()["mcp"] == "/mcp/"


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "toolbridge-mcp",
        "environment": "development",
    }


def test_readiness(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["ready"] is True
    assert {item["name"] for item in body["checks"]} >= {
        "lifecycle",
        "registry",
        "tool_lifecycle",
        "provider_router",
    }


def test_operations_snapshot_is_safe_and_complete(client: TestClient) -> None:
    response = client.get("/operations/snapshot")

    assert response.status_code == 200
    body = response.json()
    assert body["system"]["version"] == "1.1.0"
    assert isinstance(body["providers"], list)
    for p in body["providers"]:
        assert "provider" in p
        assert "status" in p
    assert len(body["tools"]) == 7
    assert set(body) == {
        "system",
        "readiness",
        "providers",
        "models",
        "tools",
        "metrics",
        "costs",
        "logs",
    }


def test_mcp_protocol_discovery_and_execution(client: TestClient) -> None:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    # A developer .env may enable MCP auth; send the configured token if so.
    token = get_settings().mcp_auth_token_value
    if token:
        headers["Authorization"] = f"Bearer {token}"
    initialize = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "toolbridge-tests", "version": "1.0"},
            },
        },
    )
    discovered = client.post(
        "/mcp/",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    executed = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "system_status", "arguments": {}},
        },
    )

    assert initialize.status_code == 200
    assert initialize.json()["result"]["capabilities"]["tools"] == {"listChanged": False}
    assert discovered.status_code == 200
    tools = discovered.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "csv_analysis",
        "currency_converter",
        "llm_analysis",
        "sql_query",
        "stock_price",
        "system_status",
        "website_reader",
    ]
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name["stock_price"]["inputSchema"]["required"]) == {"symbol"}
    assert "current_price" in by_name["stock_price"]["outputSchema"]["properties"]
    assert "summaries" in by_name["csv_analysis"]["outputSchema"]["properties"]
    assert "conversions" in by_name["currency_converter"]["outputSchema"]["properties"]
    assert "content" in by_name["llm_analysis"]["outputSchema"]["properties"]
    assert "rows" in by_name["sql_query"]["outputSchema"]["properties"]
    assert "text" in by_name["website_reader"]["outputSchema"]["properties"]
    assert by_name["system_status"]["inputSchema"]["properties"] == {}
    assert executed.status_code == 200
    result = executed.json()["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["service"] == "toolbridge-mcp"
    assert result["structuredContent"]["status"] == "ok"
