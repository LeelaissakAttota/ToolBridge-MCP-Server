"""Provider-neutral contracts for multi-currency conversion."""

from datetime import date, datetime
from enum import StrEnum
from math import isfinite
from re import fullmatch

from pydantic import Field, field_validator, model_validator

from toolbridge.core.contracts import ToolInput, ToolOutput


class CurrencyProviderName(StrEnum):
    """Supported exchange-rate provider identifiers."""

    FRANKFURTER = "frankfurter"


class CurrencyConverterInput(ToolInput):
    """Validated amount and one or more destination currencies."""

    amount: float = Field(gt=0, le=1_000_000_000_000)
    source_currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    target_currencies: list[str] = Field(min_length=1, max_length=20)

    @field_validator("amount")
    @classmethod
    def require_finite_amount(cls, value: float) -> float:
        """Reject non-finite monetary values."""

        if not isfinite(value):
            raise ValueError("amount must be finite")
        return value

    @field_validator("source_currency", mode="before")
    @classmethod
    def normalize_source(cls, value: object) -> object:
        """Normalize a source ISO currency code."""

        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("target_currencies", mode="before")
    @classmethod
    def normalize_targets(cls, value: object) -> object:
        """Normalize target ISO currency codes before strict validation."""

        if isinstance(value, list):
            return [item.strip().upper() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def require_distinct_targets(self) -> "CurrencyConverterInput":
        """Reject duplicate targets and conversions to the source currency."""
        if any(fullmatch(r"[A-Z]{3}", currency) is None for currency in self.target_currencies):
            raise ValueError("target_currencies must contain ISO currency codes")

        if len(self.target_currencies) != len(set(self.target_currencies)):
            raise ValueError("target_currencies cannot contain duplicates")
        if self.source_currency in self.target_currencies:
            raise ValueError("target_currencies cannot contain source_currency")
        return self


class CurrencyRateSet(ToolOutput):
    """Normalized provider response containing base-unit exchange rates."""

    base_currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    rates: dict[str, float] = Field(min_length=1, max_length=20)
    rate_date: date
    provider: CurrencyProviderName

    @field_validator("rates")
    @classmethod
    def require_positive_finite_rates(cls, value: dict[str, float]) -> dict[str, float]:
        """Reject unusable exchange rates."""

        if any(fullmatch(r"[A-Z]{3}", currency) is None for currency in value):
            raise ValueError("exchange-rate keys must be ISO currency codes")
        if any(
            rate <= 0 or rate > 1_000_000_000_000 or not isfinite(rate) for rate in value.values()
        ):
            raise ValueError("exchange rates must be positive, finite, and bounded")
        return value


class CurrencyConversion(ToolOutput):
    """One normalized destination conversion."""

    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    rate: float = Field(gt=0)

    @field_validator("rate", "amount")
    @classmethod
    def require_finite_values(cls, value: float) -> float:
        """Reject non-finite conversion values."""

        if not isfinite(value):
            raise ValueError("conversion values must be finite")
        return value

    amount: float = Field(ge=0)


class CurrencyConverterOutput(ToolOutput):
    """Structured multi-currency conversion result."""

    source_currency: str = Field(min_length=3, max_length=3)
    source_amount: float = Field(gt=0)
    conversions: list[CurrencyConversion] = Field(min_length=1, max_length=20)
    rate_date: date
    provider: CurrencyProviderName
    fetched_at: datetime
    cached: bool = False

    @field_validator("fetched_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        """Require an offset-aware retrieval timestamp."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must include a timezone")
        return value
