"""Provider factory and registry."""

import logging

from mcp_server.providers.cerebras import CerebrasProvider
from mcp_server.providers.nvidia import NvidiaProvider
from mcp_server.providers.openrouter import OpenRouterProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating and managing provider instances.

    Responsibilities:
    - Register provider classes
    - Create provider instances
    - Manage provider lifecycle
    - List available providers
    - Check provider health/availability
    """

    _provider_classes: dict[str, type] = {
        "cerebras": CerebrasProvider,
        "nvidia": NvidiaProvider,
        "openrouter": OpenRouterProvider,
    }

    def __init__(self):
        self._instances: dict = {}

    def register(self, name: str, provider_class: type) -> None:
        """Register a new provider class.

        Args:
            name: Provider name (e.g., 'custom')
            provider_class: Provider class implementing ProviderBase
        """
        if name in self._provider_classes:
            logger.warning(f"Overriding existing provider: {name}")
        self._provider_classes[name] = provider_class
        logger.info(f"Registered provider class: {name}")

    def unregister(self, name: str) -> bool:
        """Unregister a provider class.

        Args:
            name: Provider name to unregister

        Returns:
            True if provider was found and removed
        """
        if name in self._provider_classes:
            del self._provider_classes[name]
            logger.info(f"Unregistered provider class: {name}")
            return True
        return False

    def get_provider_class(self, name: str) -> type:
        """Get provider class by name.

        Args:
            name: Provider name

        Returns:
            Provider class

        Raises:
            KeyError: If provider not found
        """
        if name not in self._provider_classes:
            raise KeyError(f"Provider class not found: {name}")
        return self._provider_classes[name]

    def list_provider_classes(self) -> list[str]:
        """List all registered provider class names."""
        return list(self._provider_classes.keys())

    def create(
        self,
        name: str,
        config: dict | None = None,
    ):
        """Create a provider instance.

        Args:
            name: Provider name
            config: Provider configuration (dict or ProviderConfig)

        Returns:
            Provider instance

        Raises:
            KeyError: If provider not found
        """
        if name not in self._provider_classes:
            raise KeyError(f"Provider not found: {name}")

        if config is None:
            config = {}
        if isinstance(config, dict):
            # Convert dict to ProviderConfig-like object
            from mcp_server.providers.base import ProviderConfig
            config = ProviderConfig(**config)

        provider_class = self._provider_classes[name]
        instance = provider_class(config)
        logger.info(f"Created provider instance: {name}")
        return instance

    def get_or_create(
        self,
        name: str,
        config: dict | None = None,
    ):
        """Get existing instance or create new one.

        Args:
            name: Provider name
            config: Provider configuration

        Returns:
            Provider instance
        """
        if name in self._instances:
            return self._instances[name]

        instance = self.create(name, config)
        self._instances[name] = instance
        return instance

    def register_instance(self, name: str, instance) -> None:
        """Register an existing provider instance.

        Args:
            name: Provider name
            instance: Provider instance
        """
        if name in self._instances:
            logger.warning(f"Overriding existing provider instance: {name}")
        self._instances[name] = instance
        logger.info(f"Registered provider instance: {name}")

    def unregister_instance(self, name: str) -> bool:
        """Unregister a provider instance.

        Args:
            name: Provider instance name

        Returns:
            True if instance was found and removed
        """
        if name in self._instances:
            del self._instances[name]
            logger.info(f"Unregistered provider instance: {name}")
            return True
        return False

    def get_instance(self, name: str):
        """Get provider instance by name.

        Args:
            name: Provider name

        Returns:
            Provider instance or None if not found
        """
        return self._instances.get(name)

    def list_instances(self) -> list[str]:
        """List all registered instance names."""
        return list(self._instances.keys())

    def clear_instances(self) -> None:
        """Clear all provider instances."""
        self._instances.clear()
        logger.info("Cleared all provider instances")

    def __contains__(self, name: str) -> bool:
        return name in self._provider_classes

    def __len__(self) -> int:
        return len(self._provider_classes)

    def __iter__(self):
        return iter(self._provider_classes)

    def __repr__(self) -> str:
        return f"<ProviderFactory providers={list(self._provider_classes.keys())}>"


# Global factory instance
provider_factory = ProviderFactory()