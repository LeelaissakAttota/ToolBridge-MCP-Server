"""Replaceable outbound provider adapters."""

from toolbridge.providers.adapters.cerebras import CerebrasProvider
from toolbridge.providers.adapters.nvidia import NvidiaProvider
from toolbridge.providers.adapters.openrouter import OpenRouterProvider

__all__ = ["CerebrasProvider", "NvidiaProvider", "OpenRouterProvider"]
