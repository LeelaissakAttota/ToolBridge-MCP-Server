"""Entry point for the ToolBridge MCP Server.

The ``server`` module defines a ``create_app`` function that initialises the
application, configures logging, and registers any required routes or
middleware. Concrete server implementations (e.g., FastAPI, Flask) can be
added later. For now it returns a placeholder object.
"""

from .logging.logger import logger
from .config import settings

def create_app():
    """Create and configure the server application.

    Returns:
        An application object (currently ``dict``) representing the server.
    """
    logger.info("Initializing %s", settings.APP_NAME)
    # Placeholder for actual server (FastAPI/Flask) creation
    app = {"name": settings.APP_NAME, "debug": settings.DEBUG}
    logger.debug("App configuration: %s", app)
    return app
