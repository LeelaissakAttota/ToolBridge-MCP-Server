"""Logging utilities for the ToolBridge MCP Server.

Provides a configured ``logger`` instance that respects the ``LOG_LEVEL``
setting defined in :mod:`mcp_server.config.settings`.
"""

import logging
from mcp_server.config import settings

# Create a logger for the whole package
logger = logging.getLogger(settings.APP_NAME)
logger.setLevel(settings.LOG_LEVEL)

# Console handler with a simple format
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
