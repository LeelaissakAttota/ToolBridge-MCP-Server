"""ASGI application for the ToolBridge API and MCP server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

from toolbridge import __version__
from toolbridge.adapters.logging import configure_execution_logging
from toolbridge.adapters.mcp import MCPToolAdapter
from toolbridge.adapters.mcp_security import BearerTokenMiddleware, build_transport_security
from toolbridge.bootstrap import build_core_runtime
from toolbridge.config import get_settings
from toolbridge.operations.domain.models import OperationsSnapshot, ReadinessSnapshot
from toolbridge.providers.domain.routing import ModelRoutingRecord
from toolbridge.providers.infrastructure.logging import configure_provider_logging
from toolbridge.tools.infrastructure.logging import configure_stock_logging

settings = get_settings()
execution_logger = configure_execution_logging(settings.log_level)
provider_logger = configure_provider_logging(settings.log_level)
stock_logger = configure_stock_logging(settings.log_level)
core = build_core_runtime(
    settings,
    execution_logger,
    provider_logger,
    stock_logger,
)

mcp = FastMCP(
    name=settings.app_name,
    instructions="Use ToolBridge tools to retrieve and process trusted data.",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=build_transport_security(
        settings.mcp_allowed_hosts,
        settings.mcp_allowed_origins,
    ),
)
MCPToolAdapter(mcp, core.registry, core.executor).register_tools()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Start and stop MCP, provider-router, and managed-tool resources."""

    failed = False
    try:
        core.operations.validate_startup()
        await core.tool_manager.initialize()
        await core.provider_router.initialize()
        try:
            async with mcp.session_manager.run():
                core.operations.mark_ready()
                try:
                    yield
                finally:
                    core.operations.mark_stopping()
        finally:
            await core.provider_router.close()
    except BaseException:
        failed = True
        core.operations.mark_failed("application_lifecycle")
        raise
    finally:
        try:
            await core.tool_manager.close()
        except BaseException:
            core.operations.mark_failed("tool_shutdown")
            raise
        else:
            if not failed:
                core.operations.mark_stopped()


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
        "readiness": "/ready",
        "operations": "/operations/snapshot",
        "model_routing": "/operations/model-routing",
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


@app.get("/ready", tags=["service"], response_model=ReadinessSnapshot)
async def readiness() -> ReadinessSnapshot | JSONResponse:
    """Report local traffic readiness without external provider probes."""

    snapshot = core.operations.readiness()
    if snapshot.ready:
        return snapshot
    return JSONResponse(
        status_code=503,
        content=snapshot.model_dump(mode="json"),
    )


@app.get(
    "/operations/snapshot",
    tags=["operations"],
    response_model=OperationsSnapshot,
)
async def operations_snapshot() -> OperationsSnapshot:
    """Return bounded, read-only, secret-free monitoring data."""

    return core.operations.snapshot()


@app.get(
    "/operations/model-routing",
    tags=["operations"],
    response_model=tuple[ModelRoutingRecord, ...],
)
async def operations_model_routing(limit: int = 50) -> tuple[ModelRoutingRecord, ...]:
    """Return sanitized provider/model routing and failover metadata (newest first)."""

    return core.operations.model_routing(max(1, min(limit, 200)))


mcp_asgi_app = mcp.streamable_http_app()
if (mcp_token := settings.mcp_auth_token_value) is not None:
    mcp_asgi_app = BearerTokenMiddleware(mcp_asgi_app, mcp_token)  # type: ignore[assignment]
app.mount("/mcp", mcp_asgi_app, name="mcp")
