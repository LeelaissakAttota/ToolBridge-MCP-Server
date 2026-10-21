"""Opt-in live MCP smoke check against a running ToolBridge server.

Not collected by pytest (no ``test_`` prefix). Examples::

    python tests/live/mcp_live_smoke.py                      # http://127.0.0.1:8000/mcp/
    python tests/live/mcp_live_smoke.py --port 8765
    python tests/live/mcp_live_smoke.py --url http://127.0.0.1:9000/mcp/ --analysis
    TOOLBRIDGE_SMOKE_URL=http://127.0.0.1:8765/mcp/ python tests/live/mcp_live_smoke.py

With ``TOOLBRIDGE_MCP_AUTH_TOKEN`` set (or ``--token``), the bearer token is sent.
``--analysis`` additionally calls ``hcl_curie_analysis`` (needs an enabled LLM provider).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def parse_args(
    argv: Sequence[str] | None = None, environ: dict[str, str] | None = None
) -> argparse.Namespace:
    env = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description="Live MCP smoke check for ToolBridge.")
    parser.add_argument("--host", default=env.get("TOOLBRIDGE_SMOKE_HOST", DEFAULT_HOST))
    parser.add_argument(
        "--port", type=int, default=int(env.get("TOOLBRIDGE_SMOKE_PORT", DEFAULT_PORT))
    )
    parser.add_argument(
        "--url",
        default=env.get("TOOLBRIDGE_SMOKE_URL"),
        help="Full MCP URL; overrides --host/--port.",
    )
    parser.add_argument("--token", default=env.get("TOOLBRIDGE_MCP_AUTH_TOKEN") or None)
    parser.add_argument("--analysis", action="store_true", help="Also call the LLM tool.")
    parser.add_argument("--timeout", type=float, default=60.0)
    arguments = parser.parse_args(argv)
    if not arguments.url:
        arguments.url = f"http://{arguments.host}:{arguments.port}/mcp/"
    return arguments


async def run(arguments: argparse.Namespace) -> int:
    headers = {"Authorization": f"Bearer {arguments.token}"} if arguments.token else None
    async with httpx.AsyncClient(headers=headers, timeout=arguments.timeout) as http_client:
        async with streamable_http_client(arguments.url, http_client=http_client) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = [tool.name for tool in (await session.list_tools()).tools]
                print("MCP_INITIALIZE=SUCCESS")
                print(f"MCP_URL={arguments.url}")
                print(f"TOOL_COUNT={len(names)}")
                print("TOOLS=" + ",".join(names))

                calls: list[tuple[str, dict[str, object]]] = [("system_status", {})]
                if arguments.analysis:
                    calls.append(
                        (
                            "hcl_curie_analysis",
                            {
                                "operation": "summarize",
                                "text": "ToolBridge is an MCP server that exposes validated tools.",
                                "instructions": "Reply in one short sentence.",
                            },
                        )
                    )
                failed = False
                for name, tool_arguments in calls:
                    result = await session.call_tool(name, arguments=tool_arguments)
                    failed = failed or bool(result.isError)
                    print(f"{name.upper()}_IS_ERROR={result.isError}")
                    for item in result.content:
                        text = getattr(item, "text", None)
                        if text:
                            print(text)
                return 1 if failed else 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(run(parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
