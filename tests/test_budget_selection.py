import pytest

from toolbridge.providers.application.budget_selection import select_budget_models
from toolbridge.providers.domain.models import ProviderCapabilities, ProviderModel

CAPS = ProviderCapabilities(chat=True, reasoning=True)


def _m(mid, cost=0.0, free=False, ctx=None, q=0.5, provider="openrouter"):
    return ProviderModel(
        id=mid,
        provider=provider,
        capabilities=CAPS,
        is_free=free,
        input_cost_per_million_tokens_usd=cost,
        output_cost_per_million_tokens_usd=cost,
        context_window=ctx,
        reasoning_quality=q,
    )


def test_free_model_preferred():
    out = select_budget_models(
        [_m("paid", 0.1), _m("x:free", free=True)],
        provider="openrouter",
        operation="summarize",
        prompt_tokens=100,
    )
    assert out[0].model.id == "x:free" and "free" in out[0].reason
    assert out[1].model.id == "paid"  # fallback if free fails / rate-limited


def test_no_free_uses_cheapest_paid():
    out = select_budget_models(
        [_m("big", 5.0), _m("small", 0.05), _m("mid", 0.5)],
        provider="openrouter",
        operation="summarize",
        prompt_tokens=100,
    )
    assert [c.model.id for c in out] == ["small", "mid", "big"]
    assert "cheapest paid" in out[0].reason


def test_other_provider_models_ignored():
    out = select_budget_models(
        [_m("a", 0.01, provider="groq"), _m("b", 1.0)],
        provider="openrouter",
        operation="summarize",
        prompt_tokens=10,
    )
    assert [c.model.id for c in out] == ["b"]


@pytest.mark.parametrize("operation", ["analyze"])
def test_task_aware_long_analyze(operation):
    models = [
        _m("tiny-ctx", 0.01, ctx=4_000, q=0.9),
        _m("weak", 0.02, ctx=128_000, q=0.2),
        _m("ok", 0.1, ctx=128_000, q=0.7),
    ]
    out = select_budget_models(
        models, provider="openrouter", operation=operation, prompt_tokens=10_000
    )
    assert out[0].model.id == "ok"
    assert "complex" in out[0].reason


def test_short_summary_takes_cheapest_even_if_weak():
    models = [_m("weak", 0.02, q=0.2), _m("ok", 0.1, q=0.7)]
    out = select_budget_models(
        models, provider="openrouter", operation="summarize", prompt_tokens=200
    )
    assert out[0].model.id == "weak"
