"""Unit tests for secret-safe release verification helpers."""

from scripts.verify_release import find_forbidden_keys


def test_release_payload_scan_accepts_safe_monitoring_fields() -> None:
    payload = {
        "system": {"version": "1.0.0", "health_status": "healthy"},
        "tools": [{"tool_name": "system_status", "execution_count": 0}],
        "logs": [{"event": "service_ready", "request_id": None}],
    }

    assert find_forbidden_keys(payload) == []


def test_release_payload_scan_finds_nested_sensitive_keys() -> None:
    payload = {
        "providers": [{"provider": "cerebras", "api_key": "not-safe"}],
        "nested": {"request": {"prompt_text": "not-safe"}},
    }

    assert find_forbidden_keys(payload) == [
        "$.providers[0].api_key",
        "$.nested.request.prompt_text",
    ]
