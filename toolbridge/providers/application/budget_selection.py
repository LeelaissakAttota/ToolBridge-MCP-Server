"""Low-budget, task-aware model selection used by llm_analysis in Auto mode.

Rules (applied per active provider):
1. Free models first (OpenRouter ``:free`` / zero price, as discovered by the router).
2. If no free model fits, or free ones fail/rate-limit, fall back to the cheapest
   paid models of the same provider (ascending input+output price).
3. Task-aware: short summarize -> plain cheapest; analyze / long / instruction-heavy
   prompts require a context window that fits the prompt (with headroom) and prefer
   models with reasoning_quality >= 0.5, still cheapest-first.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from toolbridge.providers.domain.models import ProviderModel

LONG_PROMPT_TOKENS = 3_000
MAX_CANDIDATES = 4


@dataclass(frozen=True, slots=True)
class BudgetChoice:
    model: ProviderModel
    reason: str


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _cost(model: ProviderModel) -> float:
    return model.input_cost_per_million_tokens_usd + model.output_cost_per_million_tokens_usd


def select_budget_models(
    models: Iterable[ProviderModel],
    *,
    provider: str | None,
    operation: str,
    prompt_tokens: int,
    max_output_tokens: int = 1_024,
    complex_request: bool = False,
    limit: int = MAX_CANDIDATES,
) -> tuple[BudgetChoice, ...]:
    """Return ordered candidates (best first) with a human-readable reason each."""

    pool = [m for m in models if m.available and (provider is None or m.provider == provider)]
    heavy = operation == "analyze" or complex_request or prompt_tokens >= LONG_PROMPT_TOKENS
    needed_ctx = int((prompt_tokens + max_output_tokens) * 1.2)
    task = "complex/long task" if heavy else "short/simple task"

    def fits(m: ProviderModel) -> bool:
        return m.context_window is None or m.context_window >= needed_ctx

    pool = [m for m in pool if fits(m)]
    if heavy:
        strong = [m for m in pool if m.reasoning_quality >= 0.5]
        pool = strong or pool
    free = sorted((m for m in pool if m.is_free), key=lambda m: (-m.reasoning_quality, m.id))
    paid = sorted((m for m in pool if not m.is_free), key=lambda m: (_cost(m), m.id))
    choices = [BudgetChoice(m, f"free model ({task})") for m in free]
    choices += [
        BudgetChoice(m, f"cheapest paid fallback ${_cost(m):.4f}/1M tokens ({task})") for m in paid
    ]
    return tuple(choices[:limit])
