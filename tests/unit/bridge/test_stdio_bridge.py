"""Tests for the Claude Desktop stdio bridge."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from toolbridge import stdio_bridge

ROOT = Path(__file__).resolve().parents[3]


def test_token_prefers_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(stdio_bridge, "PROJECT_ROOT", tmp_path)
    (tmp_path / ".env").write_text("TOOLBRIDGE_MCP_AUTH_TOKEN=from-file\n", encoding="utf-8")
    monkeypatch.setenv("TOOLBRIDGE_MCP_AUTH_TOKEN", "  from-env  ")
    assert stdio_bridge._token() == "from-env"


def test_token_falls_back_to_project_env_file(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(stdio_bridge, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("TOOLBRIDGE_MCP_AUTH_TOKEN", raising=False)
    (tmp_path / ".env").write_text(
        "# comment\nOTHER=1\nTOOLBRIDGE_MCP_AUTH_TOKEN='quoted'\n", encoding="utf-8"
    )
    assert stdio_bridge._token() == "quoted"


@pytest.mark.parametrize("content", [None, "TOOLBRIDGE_MCP_AUTH_TOKEN=\n", "OTHER=x\n"])
def test_token_is_none_when_unset_or_blank(monkeypatch, tmp_path, content) -> None:
    monkeypatch.setattr(stdio_bridge, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("TOOLBRIDGE_MCP_AUTH_TOKEN", raising=False)
    if content is not None:
        (tmp_path / ".env").write_text(content, encoding="utf-8")
    assert stdio_bridge._token() is None


def test_main_runs_the_async_bridge(monkeypatch) -> None:
    called: list[bool] = []

    async def fake_run() -> None:
        called.append(True)

    monkeypatch.setattr(stdio_bridge, "run", fake_run)
    stdio_bridge.main()
    assert called == [True]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_bridge_relays_tools_list_and_call_end_to_end(monkeypatch) -> None:
    """Start the real API, then talk MCP over stdio to the bridge like Claude Desktop."""
    monkeypatch.delenv("TOOLBRIDGE_MCP_AUTH_TOKEN", raising=False)
    port = _free_port()
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "toolbridge.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "error",
        ],
        cwd=ROOT,
        env={**os.environ, "TOOLBRIDGE_MCP_AUTH_TOKEN": ""},
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                httpx.get(f"http://127.0.0.1:{port}/health", timeout=1)
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            pytest.fail("API did not start")
        _exercise_bridge(port)
    finally:
        api.terminate()
        api.wait(timeout=10)


def _exercise_bridge(port: int) -> None:
    env = {
        **os.environ,
        "TOOLBRIDGE_BRIDGE_URL": f"http://127.0.0.1:{port}/mcp/",
        "TOOLBRIDGE_MCP_AUTH_TOKEN": "",
    }
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "toolbridge.stdio_bridge"], env=env
    )

    async def exercise() -> tuple[list[str], bool]:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = [tool.name for tool in (await session.list_tools()).tools]
                result = await session.call_tool("system_status", {})
                return tools, bool(result.isError)

    tools, is_error = asyncio.run(asyncio.wait_for(exercise(), timeout=60))

    assert "system_status" in tools and "sql_query" in tools
    assert len(tools) == 7
    assert is_error is False
