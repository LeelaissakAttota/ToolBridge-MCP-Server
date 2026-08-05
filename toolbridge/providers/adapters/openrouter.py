"""OpenRouter provider adapter."""

import httpx

from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.domain.models import ProviderName


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter implementation with optional attribution headers."""

    def __init__(
        self,
        config: OpenAICompatibleConfig,
        *,
        http_referer: str | None = None,
        app_title: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        headers = {}
        if http_referer:
            headers["HTTP-Referer"] = http_referer
        if app_title:
            headers["X-OpenRouter-Title"] = app_title
        super().__init__(
            ProviderName.OPENROUTER,
            config,
            extra_headers=headers,
            transport=transport,
        )
