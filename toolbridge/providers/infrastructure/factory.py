"""Registry-driven composition of provider plugins and routing policy."""

from collections.abc import Mapping

import httpx

from toolbridge.config import LLMProviderSettings, Settings
from toolbridge.providers.adapters.plugin import (
    ProviderPlugin,
    discover_provider_plugins,
)
from toolbridge.providers.application.budget import BudgetPolicy
from toolbridge.providers.application.ports import ProviderEventLogger, ProviderUsageRecorder
from toolbridge.providers.application.router import ProviderRegistration, ProviderRouter
from toolbridge.providers.domain.models import ProviderModel


def configured_provider_settings(
    settings: Settings,
    plugins: tuple[ProviderPlugin, ...] | None = None,
) -> dict[str, LLMProviderSettings]:
    """Resolve installed plugin settings without a central provider-name map."""

    resolved: dict[str, LLMProviderSettings] = {}
    for plugin in plugins or discover_provider_plugins():
        configured = settings.providers.get(plugin.name)
        if configured is None and plugin.settings_attribute is not None:
            value = getattr(settings, plugin.settings_attribute, None)
            configured = value if isinstance(value, LLMProviderSettings) else None
        if configured is not None:
            resolved[plugin.name] = configured
    return resolved


def build_provider_router(
    settings: Settings,
    event_logger: ProviderEventLogger | None = None,
    usage_recorder: ProviderUsageRecorder | None = None,
    *,
    transports: Mapping[str, httpx.AsyncBaseTransport] | None = None,
) -> ProviderRouter:
    """Discover, configure, and instantiate every enabled provider plugin."""

    plugins = discover_provider_plugins()
    plugin_map = {plugin.name: plugin for plugin in plugins}
    configured = configured_provider_settings(settings, plugins)
    unknown_enabled = {
        name
        for name, value in settings.providers.items()
        if value.enabled and name not in plugin_map
    }
    if unknown_enabled:
        raise ValueError(f"enabled provider plugin is not installed: {sorted(unknown_enabled)[0]}")
    unknown_priority = set(settings.provider_priority_order) - set(plugin_map)
    if unknown_priority:
        raise ValueError(
            f"provider priority plugin is not installed: {sorted(unknown_priority)[0]}"
        )

    transport_map = dict(transports or {})
    registrations: list[ProviderRegistration] = []
    for plugin in plugins:
        provider_settings = configured.get(plugin.name)
        if provider_settings is None or not provider_settings.enabled:
            continue
        effective = provider_settings.model_copy(
            update={"capabilities": provider_settings.capabilities or plugin.capabilities}
        )
        provider = plugin.factory(effective, transport_map.get(plugin.name))
        registrations.append(
            ProviderRegistration(
                provider=provider,
                retry_count=effective.retry_count,
                default_model=effective.default_model,
                capabilities=effective.capabilities or plugin.capabilities,
                budget_policy=BudgetPolicy(
                    daily_limit_usd=effective.daily_budget_usd,
                    monthly_limit_usd=effective.monthly_budget_usd,
                    per_request_limit_usd=effective.per_request_budget_usd,
                    soft_limit_ratio=effective.budget_soft_limit_ratio,
                ),
                startup_discovery=True,
                model_template=ProviderModel(
                    id=effective.default_model or "unconfigured",
                    provider=plugin.name,
                    capabilities=effective.capabilities or plugin.capabilities,
                    is_free=effective.is_free,
                    input_cost_per_million_tokens_usd=(
                        effective.input_cost_per_million_tokens_usd
                    ),
                    output_cost_per_million_tokens_usd=(
                        effective.output_cost_per_million_tokens_usd
                    ),
                    context_window=effective.context_window,
                    reasoning_quality=effective.reasoning_quality,
                ),
            )
        )

    enabled = {registration.provider.name for registration in registrations}
    explicit = tuple(name for name in settings.provider_priority_order if name in enabled)
    return ProviderRouter(
        registrations=tuple(registrations),
        priority=explicit,
        retry_backoff_seconds=settings.provider_retry_backoff_seconds,
        max_retry_backoff_seconds=settings.provider_max_retry_backoff_seconds,
        max_request_bytes=settings.provider_max_request_bytes,
        event_logger=event_logger,
        usage_recorder=usage_recorder,
        installed_providers=tuple(plugin.name for plugin in plugins),
        installed_capabilities={plugin.name: plugin.capabilities for plugin in plugins},
    )
