"""Stock price providers."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from mcp_server.services.finance.exceptions import (
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
)
from mcp_server.services.finance.finance_provider import BaseFinanceProvider, ProviderHealth

logger = logging.getLogger(__name__)


class YahooFinanceProvider(BaseFinanceProvider):
    """Yahoo Finance provider (free, no API key required)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("yahoo_finance", config)
        self._base_url = "https://query1.finance.yahoo.com"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "ToolBridge-MCP/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote from Yahoo Finance."""
        cache_key = f"quote:{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        start_time = time.perf_counter()
        client = await self._get_client()

        for attempt in range(self.max_retries + 1):
            try:
                # Use Yahoo Finance v8 chart API
                url = f"{self._base_url}/v8/finance/chart/{symbol}"
                params = {
                    "interval": "1d",
                    "range": "1d",
                    "includePrePost": "false",
                }
                response = await client.get(url, params=params)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 429:
                    raise RateLimitError(self.name, retry_after=60)
                if response.status_code == 404:
                    raise SymbolNotFoundError(symbol, self.name)
                if response.status_code != 200:
                    raise ProviderError(f"HTTP {response.status_code}", self.name)

                data = response.json()
                if not data.get("chart", {}).get("result"):
                    raise SymbolNotFoundError(symbol, self.name)

                result = data["chart"]["result"][0]
                meta = result.get("meta", {})
                indicators = result.get("indicators", {}).get("quote", [{}])[0]

                current_price = meta.get("regularMarketPrice")
                if current_price is None:
                    current_price = meta.get("currentTradingPrice") or meta.get("previousClose")

                quote = {
                    "symbol": meta.get("symbol", symbol),
                    "name": meta.get("longName") or meta.get("shortName") or symbol,
                    "currency": meta.get("currency", "USD"),
                    "exchange": meta.get("exchangeName", "Unknown"),
                    "current_price": float(current_price),
                    "open": float(meta.get("regularMarketOpen", 0)),
                    "high": float(meta.get("regularMarketDayHigh", 0)),
                    "low": float(meta.get("regularMarketDayLow", 0)),
                    "previous_close": float(meta.get("previousClose", 0)),
                    "volume": int(meta.get("regularMarketVolume", 0)),
                    "change": float(current_price - meta.get("previousClose", current_price)),
                    "change_percent": float((current_price - meta.get("previousClose", current_price)) / meta.get("previousClose", 1) * 100),
                    "market_state": meta.get("marketState", "UNKNOWN"),
                    "timestamp": datetime.fromtimestamp(meta.get("regularMarketTime", datetime.now().timestamp()), tz=timezone.utc).isoformat(),
                    "source": self.name,
                }

                self._store_in_cache(cache_key, quote)
                self._record_success(latency_ms)
                return quote

            except RateLimitError:
                raise
            except SymbolNotFoundError:
                raise
            except Exception as e:
                if attempt < self.max_retries:
                    self.metrics.record_retry()
                    await self._backoff(attempt)
                    continue
                self._record_failure(str(e))
                raise ProviderError(f"Failed: {e}", self.name)

        raise ProviderError("Max retries exceeded", self.name)

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        """Yahoo Finance doesn't provide forex rates directly."""
        raise ProviderError("Exchange rates not supported", self.name)

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        return [
            {"code": c, "name": self._get_currency_name(c), "symbol": self._get_currency_symbol(c)}
            for c in ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR", "SGD", "HKD"]
        ]

    def _get_currency_name(self, code: str) -> str:
        names = {
            "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
            "JPY": "Japanese Yen", "CHF": "Swiss Franc", "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar", "NZD": "New Zealand Dollar",
            "CNY": "Chinese Yuan", "INR": "Indian Rupee", "SGD": "Singapore Dollar",
            "HKD": "Hong Kong Dollar",
        }
        return names.get(code, code)

    def _get_currency_symbol(self, code: str) -> str:
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
            "CHF": "CHF", "CAD": "C$", "AUD": "A$", "NZD": "NZ$",
            "CNY": "¥", "INR": "₹", "SGD": "S$", "HKD": "HK$",
        }
        return symbols.get(code, code)

    async def health_check(self) -> ProviderHealth:
        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/v8/finance/chart/AAPL", params={"range": "1d"})
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200 and "chart" in response.json():
                self.health.mark_healthy(latency_ms)
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
        except Exception as e:
            self.health.mark_unhealthy(str(e))
        return self.health

    async def _backoff(self, attempt: int) -> None:
        import asyncio
        delay = min(2 ** attempt, 30)
        await asyncio.sleep(delay)


class AlphaVantageProvider(BaseFinanceProvider):
    """Alpha Vantage provider (requires API key)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("alpha_vantage", config)
        self._api_key = self.config.get("api_key")
        self._base_url = "https://www.alphavantage.co/query"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "ToolBridge-MCP/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key not configured")

        cache_key = f"quote:{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        start_time = time.perf_counter()
        client = await self._get_client()

        for attempt in range(self.max_retries + 1):
            try:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol.upper(),
                    "apikey": self._api_key,
                }
                response = await client.get(self._base_url, params=params)
                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 429:
                    raise RateLimitError(self.name, retry_after=60)

                data = response.json()
                if "Error Message" in data:
                    raise SymbolNotFoundError(symbol, self.name)
                if "Note" in data and "rate limit" in data["Note"].lower():
                    raise RateLimitError(self.name, retry_after=60)

                quote_data = data.get("Global Quote", {})
                if not quote_data:
                    raise SymbolNotFoundError(symbol, self.name)

                quote = {
                    "symbol": quote_data.get("01. symbol", symbol),
                    "name": symbol,
                    "currency": "USD",
                    "exchange": "Unknown",
                    "current_price": float(quote_data.get("05. price", 0)),
                    "open": float(quote_data.get("02. open", 0)),
                    "high": float(quote_data.get("03. high", 0)),
                    "low": float(quote_data.get("04. low", 0)),
                    "previous_close": float(quote_data.get("08. previous close", 0)),
                    "volume": int(quote_data.get("06. volume", 0)),
                    "change": float(quote_data.get("09. change", 0)),
                    "change_percent": float(quote_data.get("10. change percent", "0%").rstrip("%")),
                    "market_state": "UNKNOWN",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": self.name,
                }
                self._store_in_cache(cache_key, quote)
                self._record_success(latency_ms)
                return quote

            except RateLimitError:
                raise
            except SymbolNotFoundError:
                raise
            except Exception as e:
                if attempt < self.max_retries:
                    self.metrics.record_retry()
                    await self._backoff(attempt)
                    continue
                self._record_failure(str(e))
                raise ProviderError(f"Failed: {e}", self.name)

        raise ProviderError("Max retries exceeded", self.name)

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key not configured")

        client = await self._get_client()

        if date == "latest":
            params = {
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "apikey": self._api_key,
            }
        else:
            raise ProviderError("Historical rates not supported in free tier", self.name)

        response = await client.get(self._base_url, params=params)
        if response.status_code == 429:
            raise RateLimitError(self.name)

        data = response.json()
        if "Error Message" in data:
            raise InvalidCurrencyError(from_currency if "from" in data["Error Message"] else to_currency)

        rate_data = data.get("Realtime Currency Exchange Rate", {})
        if not rate_data:
            raise ProviderError("No rate data", self.name)

        rate = float(rate_data.get("5. Exchange Rate", 0))
        return {
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "rate": rate,
            "amount": 1.0,
            "converted_amount": rate,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": datetime.now(timezone.utc).date().isoformat(),
            "source": self.name,
        }

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        return [
            {"code": c, "name": self._get_currency_name(c), "symbol": self._get_currency_symbol(c)}
            for c in ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR", "SGD", "HKD"]
        ]

    def _get_currency_name(self, code: str) -> str:
        return YahooFinanceProvider._get_currency_name(self, code)

    def _get_currency_symbol(self, code: str) -> str:
        return YahooFinanceProvider._get_currency_symbol(self, code)

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            self.health.mark_unhealthy("API key not configured")
            return self.health

        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get(self._base_url, params={
                "function": "GLOBAL_QUOTE",
                "symbol": "AAPL",
                "apikey": self._api_key,
            })
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200 and "Global Quote" in response.text:
                self.health.mark_healthy(latency_ms)
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
        except Exception as e:
            self.health.mark_unhealthy(str(e))
        return self.health

    async def _backoff(self, attempt: int) -> None:
        import asyncio
        delay = min(2 ** attempt, 30)
        await asyncio.sleep(delay)


class TwelveDataProvider(BaseFinanceProvider):
    """Twelve Data provider (requires API key)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("twelve_data", config)
        self._api_key = self.config.get("api_key")
        self._base_url = "https://api.twelvedata.com"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "ToolBridge-MCP/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key not configured")

        cache_key = f"quote:{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        try:
            response = await client.get(
                f"{self._base_url}/quote",
                params={"symbol": symbol, "apikey": self._api_key},
            )
            if response.status_code == 429:
                raise RateLimitError(self.name)
            if response.status_code != 200:
                raise ProviderError(f"HTTP {response.status_code}", self.name)

            data = response.json()
            if data.get("status") == "error":
                raise SymbolNotFoundError(symbol, self.name)

            quote = {
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "currency": data.get("currency", "USD"),
                "exchange": data.get("exchange", "Unknown"),
                "current_price": float(data.get("close", 0)),
                "open": float(data.get("open", 0)),
                "high": float(data.get("high", 0)),
                "low": float(data.get("low", 0)),
                "previous_close": float(data.get("previous_close", 0)),
                "volume": int(data.get("volume", 0)),
                "change": float(data.get("change", 0)),
                "change_percent": float(data.get("percent_change", 0)),
                "market_state": "UNKNOWN",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": self.name,
            }
            self._store_in_cache(cache_key, quote)
            return quote
        except Exception as e:
            self._record_failure(str(e))
            raise

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key not configured")

        client = await self._get_client()
        try:
            response = await client.get(
                f"{self._base_url}/exchange_rate",
                params={"symbol": f"{from_currency}/{to_currency}", "apikey": self._api_key},
            )
            if response.status_code == 429:
                raise RateLimitError(self.name)
            data = response.json()
            if data.get("status") == "error":
                raise InvalidCurrencyError(from_currency)

            rate = float(data.get("rate", 0))
            return {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": rate,
                "amount": 1.0,
                "converted_amount": rate,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date": datetime.now(timezone.utc).date().isoformat(),
                "source": self.name,
            }
        except Exception as e:
            raise ProviderError(str(e), self.name)

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        return [
            {"code": c, "name": self._get_currency_name(c), "symbol": self._get_currency_symbol(c)}
            for c in ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR"]
        ]

    def _get_currency_name(self, code: str) -> str:
        return YahooFinanceProvider._get_currency_name(self, code)

    def _get_currency_symbol(self, code: str) -> str:
        return YahooFinanceProvider._get_currency_symbol(self, code)

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            self.health.mark_unhealthy("API key not configured")
            return self.health

        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/quote", params={"symbol": "AAPL", "apikey": self._api_key})
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200 and "status" not in response.json() or response.json().get("status") != "error":
                self.health.mark_healthy(latency_ms)
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
        except Exception as e:
            self.health.mark_unhealthy(str(e))
        return self.health