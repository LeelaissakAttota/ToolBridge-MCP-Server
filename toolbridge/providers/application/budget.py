"""Process-local provider budget enforcement with safe snapshots."""

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from toolbridge.providers.domain.models import ProviderBudgetSnapshot, ProviderModel


@dataclass(frozen=True, slots=True)
class BudgetPolicy:
    """Configured provider spending limits."""

    daily_limit_usd: float | None = None
    monthly_limit_usd: float | None = None
    per_request_limit_usd: float | None = None
    soft_limit_ratio: float = 0.8


@dataclass(slots=True)
class _Spend:
    day: str
    month: str
    daily: float = 0.0
    monthly: float = 0.0


class ProviderBudgetManager:
    """Estimate and enforce configured limits without storing request content."""

    def __init__(self, policies: dict[str, BudgetPolicy] | None = None) -> None:
        self._policies = dict(policies or {})
        self._spend: dict[str, _Spend] = {}
        self._lock = Lock()

    @staticmethod
    def estimate_cost(
        model: ProviderModel,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate request cost from discovered model rates."""

        return (
            input_tokens * model.input_cost_per_million_tokens_usd
            + output_tokens * model.output_cost_per_million_tokens_usd
        ) / 1_000_000

    def permits(self, provider: str, estimate_usd: float) -> bool:
        """Return whether a request stays below every hard limit."""

        with self._lock:
            spend = self._current(provider)
            policy = self._policies.get(provider, BudgetPolicy())
            return not any(
                (
                    policy.per_request_limit_usd is not None
                    and estimate_usd > policy.per_request_limit_usd,
                    policy.daily_limit_usd is not None
                    and spend.daily + estimate_usd > policy.daily_limit_usd,
                    policy.monthly_limit_usd is not None
                    and spend.monthly + estimate_usd > policy.monthly_limit_usd,
                )
            )

    def record(self, provider: str, cost_usd: float) -> None:
        """Record actual normalized usage cost after a successful response."""

        with self._lock:
            spend = self._current(provider)
            spend.daily += max(cost_usd, 0.0)
            spend.monthly += max(cost_usd, 0.0)

    def soft_limit_reached(self, provider: str) -> bool:
        """Return whether configured daily or monthly soft limits were crossed."""

        with self._lock:
            spend = self._current(provider)
            policy = self._policies.get(provider, BudgetPolicy())
            return any(
                (
                    policy.daily_limit_usd is not None
                    and spend.daily >= policy.daily_limit_usd * policy.soft_limit_ratio,
                    policy.monthly_limit_usd is not None
                    and spend.monthly >= policy.monthly_limit_usd * policy.soft_limit_ratio,
                )
            )

    def snapshot(self, provider: str) -> ProviderBudgetSnapshot:
        """Return a non-secret immutable provider budget view."""

        with self._lock:
            spend = self._current(provider)
            policy = self._policies.get(provider, BudgetPolicy())
            hard = any(
                (
                    policy.daily_limit_usd is not None and spend.daily >= policy.daily_limit_usd,
                    policy.monthly_limit_usd is not None
                    and spend.monthly >= policy.monthly_limit_usd,
                )
            )
            soft = any(
                (
                    policy.daily_limit_usd is not None
                    and spend.daily >= policy.daily_limit_usd * policy.soft_limit_ratio,
                    policy.monthly_limit_usd is not None
                    and spend.monthly >= policy.monthly_limit_usd * policy.soft_limit_ratio,
                )
            )
            return ProviderBudgetSnapshot(
                provider=provider,
                daily_spend_usd=round(spend.daily, 8),
                monthly_spend_usd=round(spend.monthly, 8),
                daily_limit_usd=policy.daily_limit_usd,
                monthly_limit_usd=policy.monthly_limit_usd,
                per_request_limit_usd=policy.per_request_limit_usd,
                soft_limit_reached=soft,
                hard_limit_reached=hard,
            )

    def _current(self, provider: str) -> _Spend:
        now = datetime.now(UTC)
        day = now.date().isoformat()
        month = f"{now.year:04d}-{now.month:02d}"
        spend = self._spend.setdefault(provider, _Spend(day=day, month=month))
        if spend.month != month:
            spend.month = month
            spend.monthly = 0.0
        if spend.day != day:
            spend.day = day
            spend.daily = 0.0
        return spend
