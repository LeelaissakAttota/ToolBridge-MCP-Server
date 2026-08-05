"""ASGI application for the ToolBridge API and MCP server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from toolbridge import __version__
from toolbridge.adapters.logging import configure_execution_logging
from toolbridge.adapters.mcp import MCPToolAdapter
from toolbridge.bootstrap import build_core_runtime
from toolbridge.config import get_settings
from toolbridge.providers.infrastructure.logging import configure_provider_logging

settings = get_settings()
execution_logger = configure_execution_logging(settings.log_level)
provider_logger = configure_provider_logging(settings.log_level)
core = build_core_runtime(settings, execution_logger, provider_logger)

mcp = FastMCP(
    name=settings.app_name,
    instructions="Use ToolBridge tools to retrieve and process trusted data.",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
)
MCPToolAdapter(mcp, core.registry, core.executor).register_tools()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Start and stop MCP and provider resources with the application."""

    await core.provider_router.initialize()
    try:
        async with mcp.session_manager.run():
            yield
    finally:
        await core.provider_router.close()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Control plane and MCP transport for ToolBridge.",
    lifespan=lifespan,
)


@app.get("/", tags=["service"])
async def service_info() -> dict[str, str]:
    """Describe the running service and its primary endpoints."""

    return {
        "name": settings.app_name,
        "version": __version__,
        "status": "running",
        "health": "/health",
        "mcp": "/mcp/",
        "docs": "/docs",
    }


@app.get("/health", tags=["service"])
async def health() -> dict[str, str]:
    """Report liveness without depending on optional external providers."""

    return {
        "status": "ok",
        "service": "toolbridge-mcp",
        "environment": settings.environment,
    }


app.mount("/mcp", mcp.streamable_http_app(), name="mcp")
