"""OpenRouter provider adapter and plugin registration."""

from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from toolbridge.config import OpenRouterSettings
from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.adapters.plugin import ProviderPlugin, register_provider
from toolbridge.providers.domain.errors import ProviderError
from toolbridge.providers.domain.models import (
    ProviderCapabilities,
    ProviderErrorCategory,
    ProviderModel,
    ProviderName,
)

_TOKENS_PER_MILLION = 1_000_000


def _parse_price(value: object) -> float:
    """Convert a per-token price string to USD per million tokens; 0.0 on error or negative.

    OpenRouter returns -1 for auto/dynamic-routed models that have no fixed price.
    """
    try:
        return max(0.0, round(float(str(value)) * _TOKENS_PER_MILLION, 6))
    except (TypeError, ValueError):
        return 0.0


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter implementation with per-model pricing discovery and attribution headers."""

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

    async def list_models(self) -> tuple[ProviderModel, ...]:
        """Return models with per-model pricing and free-tier detection from OpenRouter."""

        payload = await self._request_json("GET", self._config.models_path)
        try:
            data = payload["data"]
            if not isinstance(data, list):
                raise TypeError
            models = []
            for item in data:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    raise TypeError
                model_id: str = item["id"]
                pricing = item.get("pricing") or {}
                input_cost = _parse_price(pricing.get("prompt", 0))
                output_cost = _parse_price(pricing.get("completion", 0))
                is_free = (input_cost == 0.0 and output_cost == 0.0) or model_id.endswith(":free")
                ctx = item.get("context_length")
                context_window = int(ctx) if isinstance(ctx, (int, float)) and ctx > 0 else None
                models.append(
                    ProviderModel(
                        id=model_id,
                        provider=self.name,
                        capabilities=self._config.capabilities,
                        is_free=is_free,
                        input_cost_per_million_tokens_usd=input_cost,
                        output_cost_per_million_tokens_usd=output_cost,
                        context_window=context_window,
                        reasoning_quality=self._config.reasoning_quality,
                        discovered_at=datetime.now(UTC),
                    )
                )
            return tuple(models)
        except (KeyError, TypeError, ValidationError) as error:
            raise ProviderError(
                ProviderErrorCategory.INVALID_RESPONSE,
                self.name,
            ) from error


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
