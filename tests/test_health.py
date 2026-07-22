"""Tests for Health and Version services."""

import pytest
import asyncio
from mcp_server.core.health import HealthService, VersionService, ServerInfo, HealthStatus


def test_server_info_creation():
    """Test ServerInfo creation with defaults."""
    info = ServerInfo()
    assert info.name == "toolbridge-mcp-server"
    assert info.version == "0.2.0"
    assert info.description == "ToolBridge MCP Server"
    assert info.protocol_version == "2024-11-05"
    assert info.started_at > 0
    assert info.uptime_seconds == 0.0


def test_server_info_update_uptime():
    """Test ServerInfo.update_uptime."""
    info = ServerInfo()
    import time
    time.sleep(0.01)
    info.update_uptime()
    assert info.uptime_seconds > 0


def test_server_info_to_dict():
    """Test ServerInfo.to_dict."""
    info = ServerInfo()
    info.update_uptime()
    d = info.to_dict()
    assert d["name"] == "toolbridge-mcp-server"
    assert d["version"] == "0.2.0"
    assert d["description"] == "ToolBridge MCP Server"
    assert "protocolVersion" in d
    assert "uptimeSeconds" in d
    assert "pythonVersion" in d
    assert "platform" in d


def test_health_status_creation():
    """Test HealthStatus creation."""
    status = HealthStatus()
    assert status.healthy is True
    assert status.checks == {}
    assert status.timestamp > 0


def test_health_status_add_check():
    """Test HealthStatus.add_check."""
    status = HealthStatus()
    status.add_check("test_check", True, {"detail": "ok"})
    assert "test_check" in status.checks
    assert status.checks["test_check"]["healthy"] is True
    assert status.checks["test_check"]["details"] == {"detail": "ok"}
    assert status.healthy is True


def test_health_status_add_failing_check():
    """Test adding failing check sets healthy to False."""
    status = HealthStatus()
    status.add_check("failing", False, {"error": "failed"})
    assert status.healthy is False
    assert status.checks["failing"]["healthy"] is False


def test_health_status_to_dict():
    """Test HealthStatus.to_dict."""
    status = HealthStatus()
    status.add_check("check1", True, {"detail": "ok"})
    status.add_check("check2", False, {"error": "bad"})
    d = status.to_dict()
    assert d["healthy"] is False
    assert "check1" in d["checks"]
    assert "check2" in d["checks"]


def test_health_service_creation():
    """Test HealthService creation."""
    health = HealthService()
    assert health is not None
    assert hasattr(health, 'check')
    assert hasattr(health, 'liveness')
    assert hasattr(health, 'readiness')


def test_health_service_register_check():
    """Test registering custom health check."""
    health = HealthService()
    health.register_check("custom", lambda: (True, {"detail": "custom ok"}))
    # Check is registered
    assert "custom" in health._custom_checks


def test_health_service_set_ready():
    """Test setting server readiness."""
    health = HealthService()
    health.set_ready(True)
    assert health._ready is True
    health.set_ready(False)
    assert health._ready is False


@pytest.mark.asyncio
async def test_health_check():
    """Test full health check."""
    health = HealthService()
    status = await health.check()
    assert isinstance(status, HealthStatus)
    assert "server" in status.checks
    assert "config" in status.checks
    assert status.checks["server"]["healthy"] is True


@pytest.mark.asyncio
async def test_liveness():
    """Test liveness probe."""
    health = HealthService()
    result = await health.liveness()
    assert result["status"] == "alive"
    assert "uptime_seconds" in result
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_readiness_not_ready():
    """Test readiness when not ready."""
    health = HealthService()
    health.set_ready(False)
    result = await health.readiness()
    assert result["status"] == "not_ready"
    assert result["reason"] == "Server not initialized"


@pytest.mark.asyncio
async def test_readiness_ready_no_checks():
    """Test readiness when ready with no custom checks."""
    health = HealthService()
    health.set_ready(True)
    result = await health.readiness()
    assert result["status"] == "ready"
    # Default server and config checks are always present
    assert "server" in result["checks"]
    assert "config" in result["checks"]


@pytest.mark.asyncio
async def test_readiness_with_passing_check():
    """Test readiness with passing custom check."""
    health = HealthService()
    health.set_ready(True)
    health.register_check("db", lambda: (True, {"connected": True}))
    result = await health.readiness()
    assert result["status"] == "ready"
    assert result["checks"]["db"]["healthy"] is True


@pytest.mark.asyncio
async def test_readiness_with_failing_check():
    """Test readiness with failing custom check."""
    health = HealthService()
    health.set_ready(True)
    health.register_check("db", lambda: (False, {"error": "connection failed"}))
    result = await health.readiness()
    assert result["status"] == "degraded"
    assert result["checks"]["db"]["healthy"] is False


@pytest.mark.asyncio
async def test_readiness_with_exception():
    """Test readiness when check raises exception."""
    health = HealthService()
    health.set_ready(True)
    health.register_check("bad", lambda: (_ for _ in ()).throw(Exception("boom")))
    result = await health.readiness()
    assert result["status"] == "degraded"
    assert result["checks"]["bad"]["healthy"] is False
    assert "boom" in result["checks"]["bad"]["details"]["error"]


@pytest.mark.asyncio
async def test_full_health():
    """Test full health check."""
    health = HealthService()
    health.set_ready(True)
    result = await health.full_health()
    assert "liveness" in result
    assert "readiness" in result
    assert "version" in result
    assert result["liveness"]["status"] == "alive"
    assert result["version"]["name"] == "toolbridge-mcp-server"


def test_version_service_creation():
    """Test VersionService creation."""
    version = VersionService()
    assert version is not None


def test_version_service_get_version():
    """Test get_version."""
    version = VersionService()
    v = version.get_version()
    assert v["version"] == "0.2.0"
    assert "protocolVersion" in v
    assert "serverName" in v


def test_version_service_get_full_info():
    """Test get_full_info."""
    version = VersionService()
    info = version.get_full_info()
    assert info["name"] == "toolbridge-mcp-server"
    assert info["version"] == "0.2.0"
    assert "uptimeSeconds" in info
    assert "pythonVersion" in info


def test_global_instances():
    """Test global health_service and version_service instances."""
    from mcp_server.core.health import health_service, version_service
    assert health_service is not None
    assert version_service is not None
    assert isinstance(health_service, HealthService)
    assert isinstance(version_service, VersionService)