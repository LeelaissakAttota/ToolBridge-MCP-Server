"""NVIDIA provider adapter."""

import httpx

from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.domain.models import ProviderName


class NvidiaProvider(OpenAICompatibleProvider):
    """NVIDIA implementation of the provider lifecycle interface."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(ProviderName.NVIDIA, config, transport=transport)
