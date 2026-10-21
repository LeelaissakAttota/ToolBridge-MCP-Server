"""Cerebras OpenAI-compatible provider adapter and plugin registration."""

import httpx

from toolbridge.config import LLMProviderSettings
from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.adapters.plugin import ProviderPlugin, register_provider
from toolbridge.providers.domain.models import ProviderCapabilities, ProviderName


class CerebrasProvider(OpenAICompatibleProvider):
    """Cerebras provider adapter."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(ProviderName.CEREBRAS, config, transport=transport)


def _create(settings: object, transport: httpx.AsyncBaseTransport | None) -> CerebrasProvider:
    if not isinstance(settings, LLMProviderSettings):
        raise TypeError("invalid Cerebras provider settings")
    return CerebrasProvider(OpenAICompatibleConfig.from_settings(settings), transport=transport)


register_provider(
    ProviderPlugin(
        name=ProviderName.CEREBRAS,
        factory=_create,
        settings_attribute="cerebras",
        capabilities=ProviderCapabilities(
            chat=True,
            reasoning=True,
            streaming=True,
            tool_use=True,
            function_calling=True,
            long_context=True,
            json_mode=True,
            code_generation=True,
        ),
    )
)
