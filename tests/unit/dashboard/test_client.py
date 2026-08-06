"""Tests for the dashboard's validated read-only HTTP client."""

import httpx
import pytest

from toolbridge.dashboard.client import DashboardClient, DashboardUnavailableError


def test_dashboard_client_requests_only_the_safe_snapshot_endpoint() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "system": {
                    "version": "0.6.0",
                    "uptime_seconds": 1.0,
                    "environment": "test",
                    "current_phase": "Phase 6",
                    "health_status": "healthy",
                    "lifecycle": "ready",
                    "started_at": "2026-08-06T00:00:00Z",
                },
                "readiness": {
                    "status": "ready",
                    "ready": True,
                    "checked_at": "2026-08-06T00:00:01Z",
                    "checks": [],
                },
                "providers": [],
                "tools": [],
                "metrics": {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "error_categories": {},
                    "average_response_time_ms": 0.0,
                    "provider_usage": {},
                    "tool_usage": {},
                },
                "costs": {
                    "estimated_token_usage": 0,
                    "estimated_api_cost_usd": 0.0,
                    "requests_per_provider": {},
                    "cost_per_provider": {},
                },
                "logs": [],
            },
            request=request,
        )

    client = DashboardClient(
        "http://127.0.0.1:8000",
        1.0,
        transport=httpx.MockTransport(handler),
    )

    snapshot = client.fetch_snapshot()

    assert snapshot.system.version == "0.6.0"
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].url.path == "/operations/snapshot"
    assert "authorization" not in requests[0].headers


def test_dashboard_client_normalizes_transport_and_validation_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"secret": "do-not-return"}, request=request)

    client = DashboardClient(
        "http://127.0.0.1:8000",
        1.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(DashboardUnavailableError) as caught:
        client.fetch_snapshot()

    assert "secret" not in str(caught.value)

