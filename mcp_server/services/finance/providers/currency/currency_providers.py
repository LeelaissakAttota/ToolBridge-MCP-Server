"""Currency exchange providers."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from mcp_server.services.finance.exceptions import (
    ProviderError,
    ProviderUnavailableError,
    RateLimitError,
    InvalidCurrencyError,
)
from mcp_server.services.finance.finance_provider import BaseFinanceProvider, ProviderHealth

logger = logging.getLogger(__name__)


class FrankfurterProvider(BaseFinanceProvider):
    """Frankfurter API provider (ECB rates - free, no key required)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("frankfurter", config)
        self._base_url = "https://api.frankfurter.app"
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
        """Frankfurter doesn't provide stock quotes."""
        raise ProviderError("Stock quotes not supported", self.name)

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        """Get exchange rate from Frankfurter (ECB)."""
        cache_key = f"rate:{from_currency}:{to_currency}:{date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        start_time = time.perf_counter()
        client = await self._get_client()

        try:
            if date == "latest":
                url = f"{self._base_url}/latest"
            else:
                url = f"{self._base_url}/{date}"

            params = {"from": from_currency.upper(), "to": to_currency.upper()}
            response = await client.get(url, params=params)

            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 429:
                raise RateLimitError(self.name, retry_after=60)
            if response.status_code == 400:
                raise InvalidCurrencyError(f"{from_currency}/{to_currency}")
            if response.status_code != 200:
                raise ProviderError(f"HTTP {response.status_code}", self.name)

            data = response.json()
            rate = data.get("rates", {}).get(to_currency.upper())
            if rate is None:
                raise InvalidCurrencyError(to_currency)

            result = {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": float(rate),
                "amount": 1.0,
                "converted_amount": float(rate),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date": data.get("date", date if date != "latest" else datetime.now(timezone.utc).date().isoformat()),
                "source": "frankfurter.app (ECB)",
            }
            self._store_in_cache(cache_key, result)
            self._record_success(latency_ms)
            return result

        except RateLimitError:
            raise
        except InvalidCurrencyError:
            raise
        except Exception as e:
            self._record_failure(str(e))
            raise ProviderError(f"Failed: {e}", self.name)

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        """Get all supported currencies from Frankfurter."""
        cache_key = "currencies"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        try:
            response = await client.get(f"{self._base_url}/currencies")
            if response.status_code != 200:
                return self._fallback_currencies()

            data = response.json()
            currencies = [
                {"code": code, "name": name, "symbol": self._get_symbol(code)}
                for code, name in data.items()
            ]
            self._store_in_cache(cache_key, currencies)
            return currencies
        except Exception as e:
            logger.warning(f"Failed to fetch currencies from Frankfurter: {e}")
            return self._fallback_currencies()

    def _fallback_currencies(self) -> list[dict[str, Any]]:
        """Fallback major currencies."""
        majors = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR", "SGD", "HKD", "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "RON", "BRL", "MXN", "KRW", "TRY", "ZAR", "RUB"]
        return [
            {"code": c, "name": self._get_name(c), "symbol": self._get_symbol(c)}
            for c in majors
        ]

    def _get_name(self, code: str) -> str:
        names = {
            "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
            "JPY": "Japanese Yen", "CHF": "Swiss Franc", "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar", "NZD": "New Zealand Dollar",
            "CNY": "Chinese Yuan", "INR": "Indian Rupee", "SGD": "Singapore Dollar",
            "HKD": "Hong Kong Dollar", "SEK": "Swedish Krona", "NOK": "Norwegian Krone",
            "DKK": "Danish Krone", "PLN": "Polish Zloty", "CZK": "Czech Koruna",
            "HUF": "Hungarian Forint", "RON": "Romanian Leu", "BRL": "Brazilian Real",
            "MXN": "Mexican Peso", "KRW": "South Korean Won", "TRY": "Turkish Lira",
            "ZAR": "South African Rand", "RUB": "Russian Ruble",
        }
        return names.get(code, code)

    def _get_symbol(self, code: str) -> str:
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
            "CHF": "CHF", "CAD": "C$", "AUD": "A$", "NZD": "NZ$",
            "CNY": "¥", "INR": "₹", "SGD": "S$", "HKD": "HK$",
            "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "zł",
            "CZK": "Kč", "HUF": "Ft", "RON": "lei", "BRL": "R$",
            "MXN": "$", "KRW": "₩", "TRY": "₺", "ZAR": "R", "RUB": "₽",
        }
        return symbols.get(code, code)

    async def health_check(self) -> ProviderHealth:
        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/latest", params={"from": "USD", "to": "EUR"})
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200:
                self.health.mark_healthy(latency_ms)
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
        except Exception as e:
            self.health.mark_unhealthy(str(e))
        return self.health


class ExchangeRateAPIProvider(BaseFinanceProvider):
    """ExchangeRate-API provider (free tier)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("exchangerate_api", config)
        self._base_url = "https://open.er-api.com/v6"
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
        raise ProviderError("Stock quotes not supported", self.name)

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        cache_key = f"rate:{from_currency}:{to_currency}:{date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        start_time = time.perf_counter()
        client = await self._get_client()

        try:
            if date == "latest":
                url = f"{self._base_url}/latest/{from_currency.upper()}"
            else:
                # Free tier doesn't support historical
                raise ProviderError("Historical rates not supported in free tier", self.name)

            response = await client.get(url)
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 429:
                raise RateLimitError(self.name, retry_after=60)
            if response.status_code != 200:
                raise ProviderError(f"HTTP {response.status_code}", self.name)

            data = response.json()
            if data.get("result") == "error":
                raise InvalidCurrencyError(f"{from_currency}/{to_currency}")

            rate = data.get("rates", {}).get(to_currency.upper())
            if rate is None:
                raise InvalidCurrencyError(to_currency)

            result = {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": float(rate),
                "amount": 1.0,
                "converted_amount": float(rate),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date": datetime.now(timezone.utc).date().isoformat(),
                "source": "exchangerate-api.com",
            }
            self._store_in_cache(cache_key, result)
            self._record_success(latency_ms)
            return result

        except RateLimitError:
            raise
        except InvalidCurrencyError:
            raise
        except Exception as e:
            self._record_failure(str(e))
            raise ProviderError(f"Failed: {e}", self.name)

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        cache_key = "currencies"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        client = await self._get_client()
        try:
            response = await client.get(f"{self._base_url}/currencies")
            if response.status_code != 200:
                return self._fallback_currencies()

            data = response.json()
            currencies = [
                {"code": code, "name": name, "symbol": self._get_symbol(code)}
                for code, name in data.items()
            ]
            self._store_in_cache(cache_key, currencies)
            return currencies
        except Exception as e:
            logger.warning(f"Failed to fetch currencies from ExchangeRate-API: {e}")
            return self._fallback_currencies()

    def _fallback_currencies(self) -> list[dict[str, Any]]:
        majors = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR", "SGD", "HKD"]
        return [
            {"code": c, "name": self._get_name(c), "symbol": self._get_symbol(c)}
            for c in majors
        ]

    def _get_name(self, code: str) -> str:
        names = {
            "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
            "JPY": "Japanese Yen", "CHF": "Swiss Franc", "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar", "NZD": "New Zealand Dollar",
            "CNY": "Chinese Yuan", "INR": "Indian Rupee", "SGD": "Singapore Dollar",
            "HKD": "Hong Kong Dollar", "SEK": "Swedish Krona", "NOK": "Norwegian Krone",
            "DKK": "Danish Krone", "PLN": "Polish Zloty", "CZK": "Czech Koruna",
            "HUF": "Hungarian Forint", "RON": "Romanian Leu", "BRL": "Brazilian Real",
            "MXN": "Mexican Peso", "KRW": "South Korean Won", "TRY": "Turkish Lira",
            "ZAR": "South African Rand", "RUB": "Russian Ruble",
        }
        return names.get(code, code)

    def _get_symbol(self, code: str) -> str:
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
            "CHF": "CHF", "CAD": "C$", "AUD": "A$", "NZD": "NZ$",
            "CNY": "¥", "INR": "₹", "SGD": "S$", "HKD": "HK$",
            "SEK": "kr", "NOK": "kr", "DKK": "kr", "PLN": "zł",
            "CZK": "Kč", "HUF": "Ft", "RON": "lei", "BRL": "R$",
            "MXN": "$", "KRW": "₩", "TRY": "₺", "ZAR": "R", "RUB": "₽",
        }
        return symbols.get(code, code)

    async def health_check(self) -> ProviderHealth:
        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/latest/USD")
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200 and response.json().get("result") != "error":
                self.health.mark_healthy(latency_ms)
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
        except Exception as e:
            self.health.mark_unhealthy(str(e))
        return self.health


class CurrencyLayerProvider(BaseFinanceProvider):
    """CurrencyLayer provider (requires API key)."""

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("currencylayer", config)
        self._api_key = self.config.get("api_key")
        self._base_url = "http://api.currencylayer.com"
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
        raise ProviderError("Stock quotes not supported", self.name)

    async def get_exchange_rate(self, from_currency: str, to_currency: str, date: str = "latest") -> dict[str, Any]:
        if not self._api_key:
            raise ProviderUnavailableError(self.name, "API key not configured")

        cache_key = f"rate:{from_currency}:{to_currency}:{date}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        start_time = time.perf_counter()
        client = await self._get_client()

        try:
            if date == "latest":
                url = f"{self._base_url}/live"
            else:
                url = f"{self._base_url}/historical"

            params = {
                "access_key": self._api_key,
                "source": from_currency.upper(),
                "currencies": to_currency.upper(),
            }
            if date != "latest":
                params["date"] = date

            response = await client.get(url, params=params)
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 429:
                raise RateLimitError(self.name, retry_after=60)
            if response.status_code != 200:
                raise ProviderError(f"HTTP {response.status_code}", self.name)

            data = response.json()
            if not data.get("success", True):
                error = data.get("error", {})
                raise InvalidCurrencyError(f"{from_currency}/{to_currency}")

            quotes = data.get("quotes", {})
            key = f"{from_currency.upper()}{to_currency.upper()}"
            rate = quotes.get(key)
            if rate is None:
                raise InvalidCurrencyError(to_currency)

            result = {
                "from_currency": from_currency.upper(),
                "to_currency": to_currency.upper(),
                "rate": float(rate),
                "amount": 1.0,
                "converted_amount": float(rate),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "date": date if date != "latest" else datetime.now(timezone.utc).date().isoformat(),
                "source": "currencylayer",
            }
            self._store_in_cache(cache_key, result)
            self._record_success(latency_ms)
            return result

        except RateLimitError:
            raise
        except InvalidCurrencyError:
            raise
        except Exception as e:
            self._record_failure(str(e))
            raise ProviderError(f"Failed: {e}", self.name)

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        cache_key = "currencies"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        if not self._api_key:
            return self._fallback_currencies()

        client = await self._get_client()
        try:
            response = await client.get(f"{self._base_url}/list", params={"access_key": self._api_key})
            if response.status_code != 200:
                return self._fallback_currencies()

            data = response.json()
            currencies = data.get("currencies", {})
            result = [
                {"code": code, "name": name, "symbol": self._get_symbol(code)}
                for code, name in currencies.items()
            ]
            self._store_in_cache(cache_key, result)
            return result
        except Exception as e:
            logger.warning(f"Failed to fetch currencies from CurrencyLayer: {e}")
            return self._fallback_currencies()

    def _fallback_currencies(self) -> list[dict[str, Any]]:
        majors = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "CNY", "INR", "SGD", "HKD"]
        return [
            {"code": c, "name": self._get_name(c), "symbol": self._get_symbol(c)}
            for c in majors
        ]

    def _get_name(self, code: str) -> str:
        return FrankfurterProvider._fallback_currencies.__self__._get_name(self, code) if hasattr(self, '_get_name') else code

    def _get_symbol(self, code: str) -> str:
        symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
            "CHF": "CHF", "CAD": "C$", "AUD": "A$", "NZD": "NZ$",
            "CNY": "¥", "INR": "₹", "SGD": "S$", "HKD": "HK$",
        }
        return symbols.get(code, code)

    async def health_check(self) -> ProviderHealth:
        if not self._api_key:
            self.health.mark_unhealthy("API key not configured")
            return self.health

        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get(f"{self._base_url}/live", params={"access_key": self._api_key, "source": "USD", "currencies": "EUR"})
            latency_ms = (time.perf_counter() - start_time) * 1000

            if response.status_code == 200 and response.json().get("success", True):
                self.health.mark_healthy(latency_ms)
            else:
                self.health.mark_unhealthy(f"HTTP {response.status_code}")
        except Exception as e:
            self.health.mark_unhealthy(str(e))
        return self.health