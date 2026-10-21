"""stdio MCP bridge for desktop clients (e.g. Claude Desktop).

Forwards tools/list and tools/call to the running ToolBridge Streamable HTTP
endpoint, so every call also appears in the dashboard History/Logs.

Usage:  python -m toolbridge.stdio_bridge
Env:    TOOLBRIDGE_BRIDGE_URL (default http://127.0.0.1:8000/mcp/)
        TOOLBRIDGE_MCP_AUTH_TOKEN (optional; else read from the project .env)
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _token() -> str | None:
    token = os.environ.get("TOOLBRIDGE_MCP_AUTH_TOKEN", "").strip()
    if token:
        return token
    env_file = PROJECT_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "TOOLBRIDGE_MCP_AUTH_TOKEN":
                return value.strip().strip("'\"") or None
    return None


async def run() -> None:
    url = os.environ.get("TOOLBRIDGE_BRIDGE_URL", "http://127.0.0.1:8000/mcp/")
    token = _token()
    headers = {"Authorization": f"Bearer {token}"} if token else None
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as upstream:
            await upstream.initialize()
            server: Server = Server("toolbridge")

            @server.list_tools()
            async def list_tools() -> list[types.Tool]:
                return (await upstream.list_tools()).tools

            @server.call_tool(validate_input=False)
            async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
                return await upstream.call_tool(name, arguments or {})

            async with stdio_server() as (sin, sout):
                await server.run(sin, sout, server.create_initialization_options())


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
