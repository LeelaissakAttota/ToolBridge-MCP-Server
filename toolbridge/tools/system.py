"""Built-in diagnostic tools."""

from datetime import UTC, datetime
from typing import Any


def system_status() -> dict[str, Any]:
    """Return the current ToolBridge service status."""

    return {
        "service": "toolbridge-mcp",
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }

