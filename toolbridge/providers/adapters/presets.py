"""Preset OpenAI-compatible provider plugins configured from the dashboard setup wizard.

Settings come from ``TOOLBRIDGE_PROVIDERS__<NAME>__*`` (the generic ``providers`` map).
"""

import os
from pathlib import Path

import httpx

from toolbridge.config import LLMProviderSettings
from toolbridge.providers.adapters.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from toolbridge.providers.adapters.plugin import ProviderPlugin, register_provider
from toolbridge.providers.domain.models import ProviderCapabilities

PRESET_PROVIDER_NAMES = ("openai", "anthropic", "gemini", "groq", "custom")

_CAPABILITIES = ProviderCapabilities(
    chat=True,
    reasoning=True,
    streaming=True,
    tool_use=True,
    function_calling=True,
    long_context=True,
    json_mode=True,
    code_generation=True,
)


def _factory(name: str):
    def _create(
        settings: object, transport: httpx.AsyncBaseTransport | None
    ) -> OpenAICompatibleProvider:
        if not isinstance(settings, LLMProviderSettings):
            raise TypeError(f"invalid {name} provider settings")
        return OpenAICompatibleProvider(
            name, OpenAICompatibleConfig.from_settings(settings), transport=transport
        )

    return _create


def _configured_names() -> set[str]:
    """Only register presets the user configured, keeping the built-in set unchanged."""

    keys = list(os.environ)
    env_file = Path.cwd() / ".env"
    if env_file.is_file():
        keys += [
            line.partition("=")[0].strip() for line in env_file.read_text("utf-8").splitlines()
        ]
    return {
        name
        for name in PRESET_PROVIDER_NAMES
        if any(k.upper().startswith(f"TOOLBRIDGE_PROVIDERS__{name.upper()}__") for k in keys)
    }


for _name in sorted(_configured_names()):
    register_provider(
        ProviderPlugin(name=_name, factory=_factory(_name), capabilities=_CAPABILITIES)
    )
