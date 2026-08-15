"""Tests for typed provider configuration and composition."""

import asyncio

import httpx
import pytest
from pydantic import ValidationError

from toolbridge.config import Settings
from toolbridge.providers.adapters.cerebras import CerebrasProvider
from toolbridge.providers.domain.models import ProviderName
from toolbridge.providers.infrastructure.factory import build_provider_router


def test_default_provider_priority_uses_dynamic_ranking_and_providers_are_disabled() -> None:
    settings = Settings(_env_file=None)

    assert settings.provider_priority_order == ()

    assert settings.cerebras.enabled is False
    assert settings.nvidia.enabled is False
    assert settings.openrouter.enabled is False


def test_nested_environment_configuration_loads_and_masks_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOOLBRIDGE_CEREBRAS__ENABLED", "true")
    monkeypatch.setenv("TOOLBRIDGE_CEREBRAS__API_KEY", "test-secret-value")
    monkeypatch.setenv("TOOLBRIDGE_CEREBRAS__DEFAULT_MODEL", "test-model")
    monkeypatch.setenv("TOOLBRIDGE_CEREBRAS__RETRY_COUNT", "3")

    settings = Settings(_env_file=None)

    assert settings.cerebras.enabled is True
    assert settings.cerebras.default_model == "test-model"
    assert settings.cerebras.retry_count == 3
    assert settings.cerebras.api_key is not None
    assert settings.cerebras.api_key.get_secret_value() == "test-secret-value"
    assert "test-secret-value" not in repr(settings)


def test_enabled_provider_requires_key_and_model() -> None:
    with pytest.raises(ValidationError, match="API key"):
        Settings(
            _env_file=None,
            cerebras={"enabled": True, "base_url": "https://example.test/v1"},
        )


def test_provider_priority_accepts_partial_plugins_and_rejects_duplicates() -> None:
    settings = Settings(_env_file=None, provider_priority="cerebras,nvidia")
    assert settings.provider_priority_order == ("cerebras", "nvidia")

    with pytest.raises(ValidationError, match="duplicates"):
        Settings(
            _env_file=None,
            provider_priority="cerebras,nvidia,openrouter,cerebras",
        )


def test_provider_base_url_requires_https() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            cerebras={"base_url": "http://example.test/v1"},
        )


def test_factory_loads_enabled_provider_without_network_access() -> None:
    settings = Settings(
        _env_file=None,
        cerebras={
            "enabled": True,
            "api_key": "test-key",
            "base_url": "https://cerebras.test/v1",
            "default_model": "test-model",
            "retry_count": 0,
        },
    )
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"data": []}))
    router = build_provider_router(
        settings,
        transports={ProviderName.CEREBRAS: transport},
    )

    async def verify() -> None:
        await router.initialize()
        assert router.active_provider is ProviderName.CEREBRAS
        registration = router._providers[ProviderName.CEREBRAS]
        assert isinstance(registration.provider, CerebrasProvider)
        await router.close()

    asyncio.run(verify())
