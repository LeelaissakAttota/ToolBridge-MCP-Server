"""Self-registering provider plugin catalog and package discovery."""

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pkgutil import iter_modules
from threading import Lock

import httpx

from toolbridge.providers.application.ports import BaseProvider
from toolbridge.providers.domain.models import ProviderCapabilities

ProviderFactory = Callable[[object, httpx.AsyncBaseTransport | None], BaseProvider]


@dataclass(frozen=True, slots=True)
class ProviderPlugin:
    """Construction metadata contributed by one provider adapter module."""

    name: str
    factory: ProviderFactory
    capabilities: ProviderCapabilities
    settings_attribute: str | None = None


class ProviderPluginRegistry:
    """Thread-safe registry populated by provider module imports."""

    def __init__(self) -> None:
        self._plugins: dict[str, ProviderPlugin] = {}
        self._lock = Lock()

    def register(self, plugin: ProviderPlugin) -> None:
        """Register one unique plugin, allowing idempotent module imports."""

        with self._lock:
            existing = self._plugins.get(plugin.name)
            if existing is not None and existing != plugin:
                raise ValueError(f"provider plugin already registered: {plugin.name}")
            self._plugins[plugin.name] = plugin

    def discover(self) -> tuple[ProviderPlugin, ...]:
        """Return plugins in stable identifier order."""

        with self._lock:
            return tuple(self._plugins[name] for name in sorted(self._plugins))

    def get(self, name: str) -> ProviderPlugin | None:
        """Return one plugin when installed."""

        with self._lock:
            return self._plugins.get(name)


provider_plugins = ProviderPluginRegistry()


def register_provider(plugin: ProviderPlugin) -> None:
    """Public self-registration hook used by provider adapter modules."""

    provider_plugins.register(plugin)


def discover_provider_plugins() -> tuple[ProviderPlugin, ...]:
    """Import provider modules without maintaining a central provider list."""

    package = import_module("toolbridge.providers.adapters")
    for module in iter_modules(package.__path__):
        if module.name.startswith("_") or module.name in {"openai_compatible", "plugin"}:
            continue
        import_module(f"{package.__name__}.{module.name}")
    return provider_plugins.discover()
