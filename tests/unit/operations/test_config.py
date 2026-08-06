"""Tests for bounded dashboard, readiness, and provider-cost configuration."""

import pytest
from pydantic import ValidationError

from toolbridge.config import Settings


def test_operations_configuration_defaults_are_local_and_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.operations.dashboard_api_url.host == "127.0.0.1"
    assert settings.operations.log_capacity == 500
    assert settings.operations.recent_log_limit == 100
    assert settings.cerebras.input_cost_per_million_tokens_usd == 0


def test_operations_configuration_rejects_remote_or_unbounded_dashboard() -> None:
    with pytest.raises(ValidationError, match="loopback"):
        Settings(
            _env_file=None,
            operations={"dashboard_api_url": "https://monitor.example.com"},
        )

    with pytest.raises(ValidationError, match="cannot exceed"):
        Settings(
            _env_file=None,
            operations={"log_capacity": 10, "recent_log_limit": 11},
        )


def test_provider_cost_configuration_loads_from_nested_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TOOLBRIDGE_CEREBRAS__INPUT_COST_PER_MILLION_TOKENS_USD",
        "0.6",
    )
    monkeypatch.setenv(
        "TOOLBRIDGE_CEREBRAS__OUTPUT_COST_PER_MILLION_TOKENS_USD",
        "1.2",
    )

    settings = Settings(_env_file=None)

    assert settings.cerebras.input_cost_per_million_tokens_usd == 0.6
    assert settings.cerebras.output_cost_per_million_tokens_usd == 1.2
