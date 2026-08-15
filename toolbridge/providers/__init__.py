"""Public provider routing API."""

from toolbridge.providers.adapters.plugin import (
    ProviderPlugin,
    discover_provider_plugins,
    register_provider,
)
from toolbridge.providers.application.router import ProviderRouter
from toolbridge.providers.domain.errors import ProviderError
from toolbridge.providers.domain.models import (
    ChatMessage,
    GenerationChunk,
    GenerationRequest,
    GenerationResponse,
    ModelSelection,
    ProviderBudgetSnapshot,
    ProviderCapabilities,
    ProviderCapability,
    ProviderErrorCategory,
    ProviderModel,
    ProviderName,
    ProviderStatusSnapshot,
    RoutingTask,
)

__all__ = [
    "ChatMessage",
    "GenerationChunk",
    "GenerationRequest",
    "GenerationResponse",
    "ModelSelection",
    "ProviderBudgetSnapshot",
    "ProviderCapabilities",
    "ProviderCapability",
    "ProviderError",
    "ProviderErrorCategory",
    "ProviderModel",
    "ProviderName",
    "ProviderPlugin",
    "ProviderRouter",
    "ProviderStatusSnapshot",
    "RoutingTask",
    "discover_provider_plugins",
    "register_provider",
]
