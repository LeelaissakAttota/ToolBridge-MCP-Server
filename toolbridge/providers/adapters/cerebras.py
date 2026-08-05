"""Cerebras provider adapter."""

import httpx

from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.domain.models import ProviderName


class CerebrasProvider(OpenAICompatibleProvider):
    """Cerebras implementation of the provider lifecycle interface."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(ProviderName.CEREBRAS, config, transport=transport)
