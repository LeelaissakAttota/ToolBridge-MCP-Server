"""Alpha Vantage Global Quote adapter for the Stock Price Tool."""

from datetime import UTC, datetime
from math import isfinite

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


class AlphaVantageStockProvider(HttpStockProvider):
    """Normalize Alpha Vantage's optional Global Quote fallback."""

    def __init__(
        self,
        config: HttpStockProviderConfig,
        *,
        api_key: str,
        query_path: str,
        function_name: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            StockProviderName.ALPHA_VANTAGE,
            config,
            transport=transport,
        )
        self._api_key = api_key
        self._query_path = query_path
        self._function_name = function_name

    async def get_quote(self, symbol: str) -> StockPriceOutput:
        """Retrieve and normalize one Alpha Vantage Global Quote response."""

        payload = await self._get_json(
            self._query_path,
            params={
                "function": self._function_name,
                "symbol": symbol,
                "apikey": self._api_key,
            },
        )
        information = payload.get("Information") or payload.get("Note")
        if isinstance(information, str):
            normalized = information.lower()
            if "api key" in normalized and (
                "invalid" in normalized or "missing" in normalized
            ):
                raise self._error(StockErrorCategory.AUTHENTICATION)
            raise self._error(StockErrorCategory.RATE_LIMIT, retryable=True)
        if "Error Message" in payload:
            raise self._error(StockErrorCategory.INVALID_SYMBOL)
        raw_quote = payload.get("Global Quote")
        if not isinstance(raw_quote, dict) or not raw_quote:
            raise self._error(StockErrorCategory.INVALID_SYMBOL)

        try:
            price = self._required_number(raw_quote.get("05. price"))
            latest_day = raw_quote.get("07. latest trading day")
            if not isinstance(latest_day, str):
                raise ValueError("missing trading day")
            timestamp = datetime.strptime(latest_day, "%Y-%m-%d").replace(tzinfo=UTC)
            returned_symbol = raw_quote.get("01. symbol")
            return StockPriceOutput(
                symbol=returned_symbol if isinstance(returned_symbol, str) else symbol,
                current_price=price,
                company_name=None,
                currency=None,
                exchange=None,
                day_high=self._optional_number(raw_quote.get("03. high")),
                day_low=self._optional_number(raw_quote.get("04. low")),
                open=self._optional_number(raw_quote.get("02. open")),
                previous_close=self._optional_number(
                    raw_quote.get("08. previous close")
                ),
                market_status=MarketStatus.UNKNOWN,
                timestamp=timestamp,
                provider=self.name,
            )
        except (TypeError, ValueError, ValidationError) as error:
            raise self._error(StockErrorCategory.INVALID_RESPONSE) from error

    def _error(
        self,
        category: StockErrorCategory,
        *,
        retryable: bool = False,
    ) -> StockDataError:
        return StockDataError(category, self.name, retryable=retryable)

    @classmethod
    def _required_number(cls, value: object) -> float:
        number = cls._optional_number(value)
        if number is None:
            raise ValueError("missing numeric value")
        return number

    @staticmethod
    def _optional_number(value: object) -> float | None:
        if not isinstance(value, str):
            return None
        try:
            number = float(value)
        except ValueError:
            return None
        return number if isfinite(number) and number >= 0 else None
