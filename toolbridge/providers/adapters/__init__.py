"""Replaceable outbound provider adapters with lazy compatibility exports."""

from importlib import import_module
from typing import Any

__all__ = ["CerebrasProvider", "NvidiaProvider", "OpenRouterProvider"]

_EXPORTS = {
    "CerebrasProvider": "toolbridge.providers.adapters.cerebras",
    "NvidiaProvider": "toolbridge.providers.adapters.nvidia",
    "OpenRouterProvider": "toolbridge.providers.adapters.openrouter",
}


def __getattr__(name: str) -> Any:
    """Load built-in adapters only when explicitly requested."""

    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(name)
    return getattr(import_module(module_name), name)
