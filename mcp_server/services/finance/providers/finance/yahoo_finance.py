"""Yahoo Finance provider implementation."""

from __future__ import annotations

import logging
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
    """Yahoo Finance API provider (free, no key required)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("yahoo_finance", config)
        self._base_url = "https://query1.finance.yahoo.com"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": "ToolBridge-MCP/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for Yahoo Finance."""
        return symbol.upper().strip()

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote from Yahoo Finance."""
        symbol = self._normalize_symbol(symbol)
        cache_key = f"quote:{symbol}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        start_time = time.perf_counter()
        client = await self._get_client()

        for attempt in range(self.max_retries + 1):
            try:
                url = f"{self._base_url}/v8/finance/chart/{symbol}"
                params = {"interval": "1m", "range": "1d"}
                response = await client.get(url, params=params)

                latency_ms = (time.perf_counter() - start_time) * 1000

                if response.status_code == 429:
                    raise RateLimitError(self.name, retry_after=60)

                if response.status_code != 200:
                    raise ProviderError(f"HTTP {response.status_code}", self.name)

                data = response.json()
                result = data.get("chart", {}).get("result")
                if not result:
                    raise SymbolNotFoundError(symbol, self.name)

                quote = self._parse_quote(result[0], symbol)
                self._store_in_cache(cache_key, quote)
                self._record_success(latency_ms)
                return quote

            except RateLimitError:
                raise
            except SymbolNotFoundError:
                raise
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                if attempt < self.max_retries:
                    self.metrics.record_retry()
                    await self._backoff(attempt)
                    continue
                self._record_failure(str(e))
                raise ProviderError(f"Failed after {self.max_retries + 1} attempts: {e}", self.name)

        raise ProviderError("Max retries exceeded", self.name)

    def _parse_quote(self, data: dict[str, Any], symbol: str) -> dict[str, Any]:
        """Parse Yahoo Finance response."""
        meta = data.get("meta", {})
        timestamps = data.get("timestamp", [])
        indicators = data.get("indicators", {}).get("quote", [{}])[0]

        # Get latest values
        if timestamps:
            latest_idx = -1
            current_price = indicators.get("close", [None])[latest_idx]
            if current_price is None:
                current_price = meta.get("regularMarketPrice")
            open_price = indicators.get("open", [None])[latest_idx]
            high_price = indicators.get("high", [None])[latest_idx]
            low_price = indicators.get("low", [None])[latest_idx]
            volume = indicators.get("volume", [None])[latest_idx]
        else:
            current_price = meta.get("regularMarketPrice")
            open_price = meta.get("regularMarketOpen")
            high_price = meta.get("regularMarketDayHigh")
            low_price = meta.get("regularMarketDayLow")
            volume = meta.get("regularMarketVolume")

        previous_close = meta.get("previousClose", current_price)
        change = current_price - previous_close if current_price and previous_close else 0
        change_percent = (change / previous_close * 100) if previous_close else 0

        # Market state
        market_state = meta.get("marketState", "UNKNOWN")

        return {
            "symbol": meta.get("symbol", symbol),
            "name": meta.get("longName") or meta.get("shortName") or "Unknown",
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName", "Unknown"),
            "current_price": current_price,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "previous_close": previous_close,
            "volume": volume,
            "change": change,
            "change_percent": change_percent,
            "market_state": market_state,
            "market_cap": meta.get("marketCap"),
            "sector": meta.get("sector"),
            "industry": meta.get("industry"),
            "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
            "avg_volume": meta.get("averageDailyVolume3Month"),
            "pe_ratio": meta.get("trailingPE"),
            "dividend_yield": meta.get("dividendYield"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.name,
        }

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        """Yahoo Finance doesn't directly provide forex, fallback to synthetic."""
        # Yahoo Finance uses currency pairs like EURUSD=X
        pair = f"{from_currency}{to_currency}=X"
        try:
            quote = await self.get_stock_quote(pair)
            rate = quote.get("current_price")
            if rate is None:
                raise ProviderError("Rate not available", self.name)
            return {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": rate,
                "amount": 1.0,
                "converted_amount": rate,
                "timestamp": quote["timestamp"],
                "date": quote["timestamp"][:10],
                "source": self.name,
            }
        except SymbolNotFoundError:
            # Try reverse
            pair = f"{to_currency}{from_currency}=X"
            quote = await self.get_stock_quote(pair)
            rate = quote.get("current_price")
            if rate is None:
                raise ProviderError("Rate not available", self.name)
            return {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": 1 / rate,
                "amount": 1.0,
                "converted_amount": 1 / rate,
                "timestamp": quote["timestamp"],
                "date": quote["timestamp"][:10],
                "source": self.name,
            }

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        """Get supported currencies (major forex pairs)."""
        # Yahoo Finance supports major forex pairs
        major_pairs = [
            ("USD", "EUR"), ("USD", "GBP"), ("USD", "JPY"), ("USD", "CHF"),
            ("USD", "CAD"), ("USD", "AUD"), ("USD", "NZD"), ("USD", "CNY"),
            ("USD", "INR"), ("USD", "SGD"), ("USD", "HKD"), ("EUR", "GBP"),
            ("EUR", "JPY"), ("EUR", "CHF"), ("GBP", "JPY"), ("AUD", "JPY"),
        ]
        currencies = set()
        for from_c, to_c in major_pairs:
            currencies.add(from_c)
            currencies.add(to_c)

        return [
            {"code": c, "name": self._get_currency_name(c), "symbol": self._get_currency_symbol(c)}
            for c in sorted(currencies)
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
        """Check Yahoo Finance health."""
        start_time = time.perf_counter()
        try:
            # Try a simple request
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/v8/finance/chart/AAPL", params={"range": "1d"})
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                self.health.mark_healthy(latency_ms)
                return self.health
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
                return self.health
        except Exception as e:
            self.health.mark_unhealthy(str(e))
            return self.health

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff."""
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

                quote = self._parse_quote(quote_data, symbol)
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

    def _parse_quote(self, data: dict[str, Any], symbol: str) -> dict[str, Any]:
        return {
            "symbol": data.get("01. symbol", symbol),
            "name": symbol,
            "currency": "USD",
            "exchange": "Unknown",
            "current_price": float(data.get("05. price", 0)),
            "open": float(data.get("02. open", 0)),
            "high": float(data.get("03. high", 0)),
            "low": float(data.get("04. low", 0)),
            "previous_close": float(data.get("08. previous close", 0)),
            "volume": int(data.get("06. volume", 0)),
            "change": float(data.get("09. change", 0)),
            "change_percent": float(data.get("10. change percent", "0%").rstrip("%")),
            "market_state": "UNKNOWN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.name,
        }

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
            # Historical not in free tier
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
        # Alpha Vantage supports major currencies
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