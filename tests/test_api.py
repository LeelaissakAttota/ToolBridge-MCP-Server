"""Smoke tests for the ToolBridge ASGI application."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from mcp.types import LATEST_PROTOCOL_VERSION

from toolbridge.main import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Run one application lifespan for all endpoint smoke tests."""

    with TestClient(app, base_url="http://127.0.0.1:8000") as test_client:
        yield test_client


def test_service_info(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["version"] == "0.4.0"
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

def test_mcp_protocol_discovery_and_execution(client: TestClient) -> None:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
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
    assert initialize.json()["result"]["capabilities"]["tools"] == {
        "listChanged": False
    }
    assert discovered.status_code == 200
    tools = discovered.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["stock_price", "system_status"]
    by_name = {tool["name"]: tool for tool in tools}
    assert set(by_name["stock_price"]["inputSchema"]["required"]) == {"symbol"}
    assert "current_price" in by_name["stock_price"]["outputSchema"]["properties"]
    assert by_name["system_status"]["inputSchema"]["properties"] == {}
    assert executed.status_code == 200
    result = executed.json()["result"]
    assert result["isError"] is False
    assert result["structuredContent"]["service"] == "toolbridge-mcp"
    assert result["structuredContent"]["status"] == "ok"
