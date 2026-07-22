"""Health and version services for MCP server."""

import time
import platform
import sys
from dataclasses import dataclass, field
from typing import Any

from mcp_server.config import settings


@dataclass
class ServerInfo:
    """Server information for health/version endpoints."""

    name: str = field(default_factory=lambda: settings.APP_NAME)
    version: str = field(default_factory=lambda: "0.2.0")
    description: str = "ToolBridge MCP Server"
    protocol_version: str = "2024-11-05"
    capabilities: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    uptime_seconds: float = 0.0

    def update_uptime(self) -> None:
        """Update uptime field."""
        self.uptime_seconds = time.time() - self.started_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON response."""
        self.update_uptime()
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities,
            "startedAt": self.started_at,
            "uptimeSeconds": self.uptime_seconds,
            "pythonVersion": sys.version.split()[0],
            "platform": platform.platform(),
        }


@dataclass
class HealthStatus:
    """Health check status."""

    healthy: bool = True
    checks: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def add_check(self, name: str, healthy: bool, details: Any = None) -> None:
        """Add a health check result."""
        self.checks[name] = {
            "healthy": healthy,
            "details": details,
            "timestamp": time.time(),
        }
        if not healthy:
            self.healthy = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "healthy": self.healthy,
            "checks": self.checks,
            "timestamp": self.timestamp,
        }


class HealthService:
    """Health check service for MCP server."""

    def __init__(self, server_info: ServerInfo | None = None) -> None:
        """Initialize health service."""
        self._server_info = server_info or ServerInfo()
        self._custom_checks: dict[str, callable] = {}
        self._ready = False

    def set_ready(self, ready: bool) -> None:
        """Set server readiness."""
        self._ready = ready

    def register_check(self, name: str, check_fn: callable) -> None:
        """Register a custom health check.

        Args:
            name: Check name.
            check_fn: Async function returning (bool, details).
        """
        self._custom_checks[name] = check_fn

    async def check(self) -> HealthStatus:
        """Run all health checks.

        Returns:
            HealthStatus with results.
        """
        status = HealthStatus()

        # Basic server health
        status.add_check("server", True, {"status": "running"})

        # Configuration health
        status.add_check("config", True, {"app_name": self._server_info.name})

        # Custom checks
        for name, check_fn in self._custom_checks.items():
            try:
                if hasattr(check_fn, "__call__"):
                    result = check_fn()
                    if hasattr(result, "__await__"):
                        healthy, details = await result
                    else:
                        healthy, details = result
                    status.add_check(name, healthy, details)
            except Exception as e:
                status.add_check(name, False, {"error": str(e)})

        return status

    async def liveness(self) -> dict[str, Any]:
        """Liveness probe endpoint."""
        return {
            "status": "alive",
            "uptime_seconds": time.time() - self._server_info.started_at,
            "timestamp": time.time(),
        }

    async def readiness(self) -> dict[str, Any]:
        """Readiness probe endpoint."""
        if not self._ready:
            return {
                "status": "not_ready",
                "reason": "Server not initialized",
                "timestamp": time.time(),
            }

        status = await self.check()
        return {
            "status": "ready" if status.healthy else "degraded",
            "checks": status.checks,
            "timestamp": time.time(),
        }

    async def full_health(self) -> dict[str, Any]:
        """Full health check with all details."""
        liveness = await self.liveness()
        readiness = await self.readiness()

        return {
            "liveness": liveness,
            "readiness": readiness,
            "version": {
                "name": self._server_info.name,
                "version": self._server_info.version,
            },
        }

    def get_server_info(self) -> ServerInfo:
        """Get server info."""
        return self._server_info


class VersionService:
    """Version information service."""

    def __init__(self, server_info: ServerInfo | None = None) -> None:
        """Initialize version service."""
        self._server_info = server_info or ServerInfo()

    def get_version(self) -> dict[str, Any]:
        """Get version information."""
        return {
            "version": self._server_info.version,
            "protocolVersion": self._server_info.protocol_version,
            "serverName": self._server_info.name,
        }

    def get_full_info(self) -> dict[str, Any]:
        """Get full server information."""
        return self._server_info.to_dict()


# Global instances
_server_info = ServerInfo()
health_service = HealthService(_server_info)
version_service = VersionService(_server_info)