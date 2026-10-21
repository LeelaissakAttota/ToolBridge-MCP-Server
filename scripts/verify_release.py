"""Verify a running ToolBridge API and optional dashboard without secrets."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any

EXPECTED_TOOLS = {
    "csv_analysis",
    "currency_converter",
    "llm_analysis",
    "sql_query",
    "stock_price",
    "system_status",
    "website_reader",
}
EXPECTED_PROVIDERS = {"cerebras", "nvidia", "openrouter"}
FORBIDDEN_KEY_PARTS = {
    "api_key",
    "authorization",
    "password",
    "prompt",
    "secret",
    "tool_argument",
    "tool_input",
    "tool_output",
}


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    """Return paths containing secret- or payload-bearing key names."""

    findings: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = f"{path}.{key}"
            if any(part in key_text for part in FORBIDDEN_KEY_PARTS):
                findings.append(child_path)
            findings.extend(find_forbidden_keys(child, child_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            findings.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return findings


def _request_json(url: str, timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        payload = json.loads(response.read())
    if not isinstance(payload, dict):
        raise RuntimeError(f"{url} did not return a JSON object")
    return payload


def _post_mcp(url: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        result = json.loads(response.read())
    if response.status != 200 or not isinstance(result, dict):
        raise RuntimeError("MCP endpoint did not return a valid protocol response")
    return result


def validate_api(api_url: str, timeout_seconds: float) -> None:
    """Validate identity, MCP, liveness, readiness, registration, and monitoring."""

    service = _request_json(f"{api_url}/", timeout_seconds)
    health = _request_json(f"{api_url}/health", timeout_seconds)
    readiness = _request_json(f"{api_url}/ready", timeout_seconds)
    snapshot = _request_json(f"{api_url}/operations/snapshot", timeout_seconds)
    initialized = _post_mcp(
        f"{api_url}/mcp/",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "toolbridge-release-verifier", "version": "1.0"},
            },
        },
        timeout_seconds,
    )
    discovered = _post_mcp(
        f"{api_url}/mcp/",
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        timeout_seconds,
    )

    if service.get("version") != "1.1.0":
        raise RuntimeError("service version is not 1.1.0")
    if health.get("status") != "ok":
        raise RuntimeError("health endpoint did not report OK")
    if readiness.get("ready") is not True or readiness.get("status") != "ready":
        raise RuntimeError("readiness endpoint did not report Ready")
    if "result" not in initialized or "tools" not in initialized["result"]["capabilities"]:
        raise RuntimeError("MCP initialize did not advertise tool capability")

    discovered_tools = {item.get("name") for item in discovered.get("result", {}).get("tools", [])}
    if discovered_tools != EXPECTED_TOOLS:
        raise RuntimeError(f"MCP discovery tool set is incomplete: {sorted(discovered_tools)}")

    tool_names = {item.get("tool_name") for item in snapshot.get("tools", [])}
    provider_names = {item.get("provider") for item in snapshot.get("providers", [])}
    if tool_names != EXPECTED_TOOLS:
        raise RuntimeError(f"registered tool set is incomplete: {sorted(tool_names)}")
    if not EXPECTED_PROVIDERS.issubset(provider_names):
        raise RuntimeError(f"provider set is incomplete: {sorted(provider_names)}")

    forbidden = find_forbidden_keys(snapshot)
    if forbidden:
        raise RuntimeError(f"operations snapshot exposes forbidden keys: {forbidden}")


def validate_dashboard(dashboard_url: str, timeout_seconds: float) -> None:
    """Validate Streamlit's health endpoint and HTML application root."""

    with urllib.request.urlopen(
        f"{dashboard_url}/_stcore/health", timeout=timeout_seconds
    ) as response:
        body = response.read().decode("utf-8").strip().lower()
        if response.status != 200 or body != "ok":
            raise RuntimeError("dashboard health endpoint did not report OK")

    with urllib.request.urlopen(dashboard_url, timeout=timeout_seconds) as response:
        body = response.read(4_096).decode("utf-8", errors="replace").lower()
        if (
            response.status != 200
            or response.headers.get_content_type() != "text/html"
            or "<html" not in body
        ):
            raise RuntimeError("dashboard root did not return an HTML application")


def wait_for_release(
    api_url: str,
    dashboard_url: str | None,
    timeout_seconds: float,
) -> None:
    """Retry bounded startup checks until both release surfaces are healthy."""

    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            validate_api(api_url.rstrip("/"), min(timeout_seconds, 5.0))
            if dashboard_url is not None:
                validate_dashboard(dashboard_url.rstrip("/"), min(timeout_seconds, 5.0))
            return
        except (OSError, RuntimeError, ValueError, urllib.error.URLError) as error:
            last_error = error
            time.sleep(1.0)
    raise RuntimeError(f"release verification timed out: {last_error}") from last_error


def main() -> int:
    """Run command-line release verification."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:8501")
    parser.add_argument("--skip-dashboard", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    arguments = parser.parse_args()

    try:
        wait_for_release(
            arguments.api_url,
            None if arguments.skip_dashboard else arguments.dashboard_url,
            arguments.timeout_seconds,
        )
    except RuntimeError as error:
        print(f"release verification failed: {error}", file=sys.stderr)
        return 1
    print("ToolBridge v1.1.0 release verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
