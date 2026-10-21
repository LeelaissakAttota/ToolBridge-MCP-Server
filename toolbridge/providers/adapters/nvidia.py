"""NVIDIA OpenAI-compatible provider adapter and plugin registration."""

import httpx

from toolbridge.config import LLMProviderSettings
from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.adapters.plugin import ProviderPlugin, register_provider
from toolbridge.providers.domain.models import ProviderCapabilities, ProviderName


class NvidiaProvider(OpenAICompatibleProvider):
    """NVIDIA provider adapter."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(ProviderName.NVIDIA, config, transport=transport)


def _create(settings: object, transport: httpx.AsyncBaseTransport | None) -> NvidiaProvider:
    if not isinstance(settings, LLMProviderSettings):
        raise TypeError("invalid NVIDIA provider settings")
    return NvidiaProvider(OpenAICompatibleConfig.from_settings(settings), transport=transport)


register_provider(
    ProviderPlugin(
        name=ProviderName.NVIDIA,
        factory=_create,
        settings_attribute="nvidia",
        capabilities=ProviderCapabilities(
            chat=True,
            reasoning=True,
            streaming=True,
            embeddings=True,
            image_generation=True,
            audio_generation=True,
            tool_use=True,
            function_calling=True,
            vision=True,
            long_context=True,
            json_mode=True,
            code_generation=True,
        ),
    )
)
