"""Model routing history: Auto-mode selection, failover chain, and sanitization."""

import asyncio
from datetime import UTC, datetime

import pytest

from toolbridge.providers.application.routing_history import ModelRoutingHistory
from toolbridge.providers.domain.errors import ProviderError
from toolbridge.providers.domain.models import (
    GenerationRequest,
    GenerationResponse,
    ProviderErrorCategory,
    ProviderModel,
    TokenUsage,
)
from toolbridge.providers.domain.routing import (
    ModelRoutingRecord,
    RoutingMode,
    RoutingOutcome,
)
from toolbridge.tools.application.llm_analysis import LLMAnalysisTool
from toolbridge.tools.domain.llm_analysis import AnalysisOperation, LLMAnalysisInput
from toolbridge.tools.domain.tool_errors import LLMAnalysisUnavailableError

SECRET_DOC = "TOP-SECRET-DOCUMENT-CONTENT-12345"
SECRET_INSTR = "PRIVATE-INSTRUCTION-xyz"


class FakeRouter:
    """Duck-typed router: free model rate-limited, cheap paid model succeeds."""

    def __init__(self, failing: dict[str, ProviderErrorCategory]) -> None:
        self.failing = failing
        self.priority = ("openrouter",)
        self.routing_history = ModelRoutingHistory()

    def discovered_models(self) -> tuple[ProviderModel, ...]:
        return (
            ProviderModel(id="free-a:free", provider="openrouter", is_free=True),
            ProviderModel(
                id="cheap-b",
                provider="openrouter",
                input_cost_per_million_tokens_usd=0.1,
                output_cost_per_million_tokens_usd=0.2,
            ),
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        model = request.model or "router-default"
        if model in self.failing:
            raise ProviderError(self.failing[model], "openrouter")
        return GenerationResponse(
            provider="openrouter",
            request_id="req-123456789",
            model=model,
            content="SECRET-OUTPUT-should-not-be-recorded",
            usage=TokenUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )


def build_tool(router: FakeRouter, model: str | None = None) -> LLMAnalysisTool:
    return LLMAnalysisTool(
        router,  # type: ignore[arg-type]
        timeout_seconds=5,
        max_input_characters=10_000,
        max_tokens=100,
        temperature=0,
        model=model,
        system_prompt="system",
    )


def run(tool: LLMAnalysisTool) -> object:
    return asyncio.run(
        tool.execute(
            LLMAnalysisInput(
                operation=AnalysisOperation.SUMMARIZE, text=SECRET_DOC, instructions=SECRET_INSTR
            )
        )
    )


def test_auto_mode_records_first_choice_free_model() -> None:
    router = FakeRouter({})
    run(build_tool(router))
    (record,) = router.routing_history.recent()
    assert record.mode is RoutingMode.AUTO
    assert record.status is RoutingOutcome.SUCCEEDED
    assert record.selected_model == "free-a:free"
    assert record.selected_provider == "openrouter"
    assert "free model" in (record.selection_reason or "")
    assert record.failover is False
    assert len(record.attempts) == 1


def test_failover_chain_records_error_category() -> None:
    router = FakeRouter({"free-a:free": ProviderErrorCategory.RATE_LIMIT})
    run(build_tool(router))
    (record,) = router.routing_history.recent()
    assert record.failover is True
    assert record.selected_model == "cheap-b"
    assert "cheapest paid" in (record.selection_reason or "")
    assert [a.outcome for a in record.attempts] == [
        RoutingOutcome.FAILED,
        RoutingOutcome.SUCCEEDED,
    ]
    assert record.attempts[0].error_category == "rate_limit"
    assert record.chain() == "free-a:free (rate_limit) -> cheap-b"


def test_total_failure_is_recorded_and_raised() -> None:
    cat = ProviderErrorCategory.UNAVAILABLE
    router = FakeRouter({"free-a:free": cat, "cheap-b": cat, "router-default": cat})
    with pytest.raises(LLMAnalysisUnavailableError):
        run(build_tool(router))
    (record,) = router.routing_history.recent()
    assert record.status is RoutingOutcome.FAILED
    assert record.selected_model is None
    assert record.error_category == "unavailable"
    assert len(record.attempts) == 3


def test_fixed_model_mode() -> None:
    router = FakeRouter({})
    run(build_tool(router, model="pinned"))
    (record,) = router.routing_history.recent()
    assert record.mode is RoutingMode.FIXED
    assert record.selected_model == "pinned"
    assert record.selection_reason == "configured model"


def test_routing_metadata_never_contains_prompt_or_output() -> None:
    router = FakeRouter({"free-a:free": ProviderErrorCategory.TIMEOUT})
    run(build_tool(router))
    dumped = " ".join(r.model_dump_json() for r in router.routing_history.recent())
    for secret in (SECRET_DOC, SECRET_INSTR, "SECRET-OUTPUT", "system"):
        assert secret not in dumped


def test_history_is_bounded_and_newest_first() -> None:
    history = ModelRoutingHistory(limit=2)
    for i in range(3):
        history.record(
            ModelRoutingRecord(
                timestamp=datetime.now(UTC),
                tool="llm_analysis",
                mode=RoutingMode.AUTO,
                status=RoutingOutcome.SUCCEEDED,
                selected_model=f"m{i}",
            )
        )
    assert [r.selected_model for r in history.recent()] == ["m2", "m1"]
    with pytest.raises(ValueError):
        ModelRoutingHistory(limit=0)
