"""OpenRouter provider adapter and plugin registration."""

import httpx

from toolbridge.config import OpenRouterSettings
from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.adapters.plugin import ProviderPlugin, register_provider
from toolbridge.providers.domain.models import ProviderCapabilities, ProviderName


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


def _create(settings: object, transport: httpx.AsyncBaseTransport | None) -> OpenRouterProvider:
    if not isinstance(settings, OpenRouterSettings):
        raise TypeError("invalid OpenRouter provider settings")
    return OpenRouterProvider(
        OpenAICompatibleConfig.from_settings(settings),
        http_referer=(str(settings.http_referer) if settings.http_referer else None),
        app_title=settings.app_title,
        transport=transport,
    )


register_provider(
    ProviderPlugin(
        name=ProviderName.OPENROUTER,
        factory=_create,
        settings_attribute="openrouter",
        capabilities=ProviderCapabilities(
            chat=True,
            reasoning=True,
            streaming=True,
            embeddings=True,
            image_generation=True,
            tool_use=True,
            function_calling=True,
            vision=True,
            long_context=True,
            json_mode=True,
            web_search=True,
            code_generation=True,
        ),
    )
)
