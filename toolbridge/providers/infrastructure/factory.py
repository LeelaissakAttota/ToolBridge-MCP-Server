"""Configuration-driven composition of provider adapters and router policy."""

from collections.abc import Mapping

import httpx

from toolbridge.config import LLMProviderSettings, Settings
from toolbridge.providers.adapters.cerebras import CerebrasProvider
from toolbridge.providers.adapters.nvidia import NvidiaProvider
from toolbridge.providers.adapters.openai_compatible import OpenAICompatibleConfig
from toolbridge.providers.adapters.openrouter import OpenRouterProvider
from toolbridge.providers.application.ports import (
    ProviderEventLogger,
    ProviderUsageRecorder,
)
from toolbridge.providers.application.router import ProviderRegistration, ProviderRouter
from toolbridge.providers.domain.models import ProviderName


def build_provider_router(
    settings: Settings,
    event_logger: ProviderEventLogger | None = None,
    usage_recorder: ProviderUsageRecorder | None = None,
    *,
    transports: Mapping[ProviderName, httpx.AsyncBaseTransport] | None = None,
) -> ProviderRouter:
    """Build enabled providers in configured priority order."""

    provider_settings: dict[ProviderName, LLMProviderSettings] = {
        ProviderName.CEREBRAS: settings.cerebras,
        ProviderName.NVIDIA: settings.nvidia,
        ProviderName.OPENROUTER: settings.openrouter,
    }
    transport_map = dict(transports or {})
    registrations: list[ProviderRegistration] = []
    enabled_priority: list[ProviderName] = []

    for name in settings.provider_priority_order:
        configured = provider_settings[name]
        if not configured.enabled:
            continue
        enabled_priority.append(name)
        adapter_config = _adapter_config(configured)
        transport = transport_map.get(name)
        if name is ProviderName.CEREBRAS:
            provider = CerebrasProvider(adapter_config, transport=transport)
        elif name is ProviderName.NVIDIA:
            provider = NvidiaProvider(adapter_config, transport=transport)
        else:
            openrouter = settings.openrouter
            provider = OpenRouterProvider(
                adapter_config,
                http_referer=(
                    str(openrouter.http_referer)
                    if openrouter.http_referer is not None
                    else None
                ),
                app_title=openrouter.app_title,
                transport=transport,
            )
        registrations.append(
            ProviderRegistration(provider=provider, retry_count=configured.retry_count)
        )

    return ProviderRouter(
        registrations=tuple(registrations),
        priority=tuple(enabled_priority),
        retry_backoff_seconds=settings.provider_retry_backoff_seconds,
        max_retry_backoff_seconds=settings.provider_max_retry_backoff_seconds,
        max_request_bytes=settings.provider_max_request_bytes,
        event_logger=event_logger,
        usage_recorder=usage_recorder,
    )


def _adapter_config(settings: LLMProviderSettings) -> OpenAICompatibleConfig:
    """Unwrap credentials only at the outbound adapter composition boundary."""

    if settings.api_key is None or settings.default_model is None:
        raise ValueError("enabled provider configuration is incomplete")
    return OpenAICompatibleConfig(
        base_url=str(settings.base_url),
        api_key=settings.api_key.get_secret_value(),
        default_model=settings.default_model,
        timeout_seconds=settings.timeout_seconds,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        max_prompt_bytes=settings.max_prompt_bytes,
        models_path=settings.models_path,
        chat_completions_path=settings.chat_completions_path,
    )
