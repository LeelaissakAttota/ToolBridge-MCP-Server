"""Health and monitoring services for MCP server."""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServerInfo:
    """Server information for health/version endpoints."""

    name: str = "toolbridge-mcp-server"
    version: str = "0.1.0"
    description: str = "ToolBridge MCP Server"
    started_at: float = field(default_factory=time.time)
    uptime_seconds: float = 0.0
    transport: str = "streamable-http"
    capabilities: dict[str, Any] = field(default_factory=dict)


class VersionService:
    """Provides version and build information."""

    def __init__(self, server_info: ServerInfo | None = None) -> None:
        """Initialize version service.

        Args:
            server_info: Optional ServerInfo instance.
        """
        self._info = server_info or ServerInfo()
        logger.debug("VersionService initialized")

    def get_version(self) -> dict[str, str]:
        """Get version information.

        Returns:
            Version dict.
        """
        return {
            "name": self._info.name,
            "version": self._info.version,
            "description": self._info.description,
        }

    def get_build_info(self) -> dict[str, Any]:
        """Get detailed build information.

        Returns:
            Build info dict.
        """
        return {
            "name": self._info.name,
            "version": self._info.version,
            "description": self._info.description,
            "transport": self._info.transport,
        }


class HealthService:
    """Health check service for MCP server.

    Provides liveness and readiness probes.
    """

    def __init__(self, server_info: ServerInfo | None = None) -> None:
        """Initialize health service.

        Args:
            server_info: Optional ServerInfo instance.
        """
        self._info = server_info or ServerInfo()
        self._checks: dict[str, callable] = {}
        self._ready = False
        logger.debug("HealthService initialized")

    def register_check(self, name: str, check_fn: callable) -> None:
        """Register a health check function.

        Args:
            name: Check name.
            check_fn: Async function returning (healthy: bool, details: dict).
        """
        self._checks[name] = check_fn
        logger.debug(f"Registered health check: {name}")

    def set_ready(self, ready: bool = True) -> None:
        """Set server readiness.

        Args:
            ready: Whether server is ready.
        """
        self._ready = ready
        logger.info(f"Server readiness set to: {ready}")

    async def liveness(self) -> dict[str, Any]:
        """Liveness probe - server is alive.

        Returns:
            Liveness status.
        """
        self._info.uptime_seconds = time.time() - self._info.started_at
        return {
            "status": "alive",
            "uptime_seconds": self._info.uptime_seconds,
            "timestamp": time.time(),
        }

    async def readiness(self) -> dict[str, Any]:
        """Readiness probe - server can handle requests.

        Returns:
            Readiness status with check results.
        """
        if not self._ready:
            return {
                "status": "not_ready",
                "reason": "Server not initialized",
                "timestamp": time.time(),
            }

        results = {}
        all_healthy = True

        for name, check_fn in self._checks.items():
            try:
                healthy, details = await check_fn()
                results[name] = {"healthy": healthy, **details}
                if not healthy:
                    all_healthy = False
            except Exception as e:
                results[name] = {"healthy": False, "error": str(e)}
                all_healthy = False

        return {
            "status": "ready" if all_healthy else "degraded",
            "checks": results,
            "timestamp": time.time(),
        }

    async def full_health(self) -> dict[str, Any]:
        """Full health check with all details.

        Returns:
            Complete health status.
        """
        liveness = await self.liveness()
        readiness = await self.readiness()

        return {
            "liveness": liveness,
            "readiness": readiness,
            "version": {
                "name": self._info.name,
                "version": self._info.version,
            },
        }