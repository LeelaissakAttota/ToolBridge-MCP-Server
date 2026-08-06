"""Yahoo Finance chart adapter for the Stock Price Tool."""

from collections.abc import Callable
from datetime import UTC, datetime
from math import isfinite
from time import time
from typing import Any

import httpx
from pydantic import ValidationError

from toolbridge.tools.adapters.http import (
    HttpStockProvider,
    HttpStockProviderConfig,
)
from toolbridge.tools.domain.errors import StockDataError
from toolbridge.tools.domain.models import (
    MarketStatus,
    StockErrorCategory,
    StockPriceOutput,
    StockProviderName,
)

EpochClock = Callable[[], float]


class YahooFinanceStockProvider(HttpStockProvider):
    """Normalize Yahoo Finance chart data behind the stock provider port."""

    def __init__(
        self,
        config: HttpStockProviderConfig,
        *,
        quote_path_template: str,
        range_value: str,
        interval: str,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: EpochClock = time,
    ) -> None:
        super().__init__(
            StockProviderName.YAHOO_FINANCE,
            config,
            transport=transport,
        )
        self._quote_path_template = quote_path_template
        self._range_value = range_value
        self._interval = interval
        self._clock = clock

    async def get_quote(self, symbol: str) -> StockPriceOutput:
        """Retrieve and normalize one Yahoo chart response."""

        payload = await self._get_json(
            self._quote_path_template.format(symbol=symbol),
            params={"range": self._range_value, "interval": self._interval},
        )
        try:
            chart = self._mapping(payload.get("chart"))
            if chart.get("error") is not None:
                raise self._error(StockErrorCategory.INVALID_SYMBOL)
            results = chart.get("result")
            if not isinstance(results, list) or not results:
                raise self._error(StockErrorCategory.INVALID_SYMBOL)
            result = self._mapping(results[0])
            meta = self._mapping(result.get("meta"))
            indicators = self._mapping(result.get("indicators"))
            quote_sets = indicators.get("quote")
            quote = (
                self._mapping(quote_sets[0]) if isinstance(quote_sets, list) and quote_sets else {}
            )
            current_price = self._number(meta.get("regularMarketPrice"))
            if current_price is None:
                current_price = self._last_number(quote.get("close"))
            if current_price is None:
                raise self._error(StockErrorCategory.INVALID_RESPONSE)
            epoch = self._number(meta.get("regularMarketTime"))
            if epoch is None:
                epoch = self._last_number(result.get("timestamp"))
            if epoch is None:
                raise self._error(StockErrorCategory.INVALID_RESPONSE)
            return StockPriceOutput(
                symbol=self._text(meta.get("symbol")) or symbol,
                current_price=current_price,
                company_name=(
                    self._text(meta.get("longName")) or self._text(meta.get("shortName"))
                ),
                currency=self._text(meta.get("currency")),
                exchange=(
                    self._text(meta.get("fullExchangeName"))
                    or self._text(meta.get("exchangeName"))
                ),
                day_high=(
                    self._number(meta.get("regularMarketDayHigh"))
                    or self._max_number(quote.get("high"))
                ),
                day_low=(
                    self._number(meta.get("regularMarketDayLow"))
                    or self._min_number(quote.get("low"))
                ),
                open=(
                    self._number(meta.get("regularMarketOpen"))
                    or self._first_number(quote.get("open"))
                ),
                previous_close=(
                    self._number(meta.get("previousClose"))
                    or self._number(meta.get("chartPreviousClose"))
                ),
                market_status=self._market_status(meta),
                timestamp=datetime.fromtimestamp(epoch, UTC),
                provider=self.name,
            )
        except StockDataError:
            raise
        except (KeyError, TypeError, ValueError, OverflowError, ValidationError) as error:
            raise self._error(StockErrorCategory.INVALID_RESPONSE) from error

    def _market_status(self, meta: dict[str, Any]) -> MarketStatus:
        state = self._text(meta.get("marketState"))
        if state is not None:
            normalized = state.upper()
            if normalized.startswith("PRE"):
                return MarketStatus.PRE_MARKET
            if normalized == "REGULAR":
                return MarketStatus.OPEN
            if normalized.startswith("POST"):
                return MarketStatus.POST_MARKET
            if normalized == "CLOSED":
                return MarketStatus.CLOSED

        periods = meta.get("currentTradingPeriod")
        if not isinstance(periods, dict):
            return MarketStatus.UNKNOWN
        current = self._clock()
        for name, status in (
            ("regular", MarketStatus.OPEN),
            ("pre", MarketStatus.PRE_MARKET),
            ("post", MarketStatus.POST_MARKET),
        ):
            period = periods.get(name)
            if not isinstance(period, dict):
                continue
            start = self._number(period.get("start"))
            end = self._number(period.get("end"))
            if start is not None and end is not None and start <= current < end:
                return status
        return MarketStatus.CLOSED

    def _error(self, category: StockErrorCategory) -> StockDataError:
        return StockDataError(
            category,
            self.name,
            retryable=category
            in {
                StockErrorCategory.TIMEOUT,
                StockErrorCategory.NETWORK,
                StockErrorCategory.RATE_LIMIT,
                StockErrorCategory.UNAVAILABLE,
            },
        )

    @staticmethod
    def _mapping(value: object) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise TypeError("expected mapping")
        return value

    @staticmethod
    def _text(value: object) -> str | None:
        return value if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _number(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        number = float(value)
        return number if isfinite(number) and number >= 0 else None

    @classmethod
    def _numbers(cls, value: object) -> list[float]:
        if not isinstance(value, list):
            return []
        return [number for item in value if (number := cls._number(item)) is not None]

    @classmethod
    def _first_number(cls, value: object) -> float | None:
        values = cls._numbers(value)
        return values[0] if values else None

    @classmethod
    def _last_number(cls, value: object) -> float | None:
        values = cls._numbers(value)
        return values[-1] if values else None

    @classmethod
    def _max_number(cls, value: object) -> float | None:
        values = cls._numbers(value)
        return max(values) if values else None

    @classmethod
    def _min_number(cls, value: object) -> float | None:
        values = cls._numbers(value)
        return min(values) if values else None
