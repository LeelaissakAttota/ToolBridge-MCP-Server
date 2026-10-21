"""Shared bounded HTTP behavior for stock data adapters."""

import json
from abc import abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import httpx

from toolbridge.tools.application.ports import StockQuoteProvider
from toolbridge.tools.domain.errors import StockDataError
from toolbridge.tools.domain.models import (
    ProviderHealthStatus,
    StockErrorCategory,
    StockPriceOutput,
    StockProviderName,
    ToolHealthState,
)


@dataclass(frozen=True, slots=True)
class HttpStockProviderConfig:
    """Validated infrastructure values consumed by HTTP stock adapters."""

    base_url: str
    timeout_seconds: float
    max_response_bytes: int
    user_agent: str


class HttpStockProvider(StockQuoteProvider):
    """Base adapter with safe HTTP errors and explicit lifecycle."""

    def __init__(
        self,
        name: StockProviderName,
        config: HttpStockProviderConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._name = name
        self._config = config
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> StockProviderName:
        """Return the stable provider identifier."""

        return self._name

    async def initialize(self) -> None:
        """Create the bounded asynchronous HTTP client once."""

        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=httpx.Timeout(self._config.timeout_seconds),
            headers={
                "Accept": "application/json",
                "User-Agent": self._config.user_agent,
            },
            follow_redirects=False,
            transport=self._transport,
        )

    async def health_check(self, symbol: str) -> ProviderHealthStatus:
        """Probe quote retrieval and normalize health without raising."""

        started_at = perf_counter()
        try:
            await self.get_quote(symbol)
        except StockDataError as error:
            return ProviderHealthStatus(
                provider=self.name,
                status=ToolHealthState.UNAVAILABLE,
                checked_at=datetime.now(UTC),
                latency_ms=self._duration_ms(started_at),
                error_category=error.category,
            )
        return ProviderHealthStatus(
            provider=self.name,
            status=ToolHealthState.HEALTHY,
            checked_at=datetime.now(UTC),
            latency_ms=self._duration_ms(started_at),
        )

    async def close(self) -> None:
        """Close the HTTP client idempotently."""

        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, str],
    ) -> dict[str, Any]:
        client = self._client
        if client is None:
            raise StockDataError(
                StockErrorCategory.UNAVAILABLE,
                self.name,
                retryable=False,
            )
        try:
            async with client.stream("GET", path, params=params) as response:
                self._raise_for_status(response.status_code)
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        declared_length = int(content_length)
                    except ValueError as error:
                        raise self._invalid_response() from error
                    if declared_length > self._config.max_response_bytes:
                        raise self._invalid_response()

                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > self._config.max_response_bytes:
                        raise self._invalid_response()
                    content.extend(chunk)
        except StockDataError:
            raise
        except httpx.TimeoutException as error:
            raise StockDataError(
                StockErrorCategory.TIMEOUT,
                self.name,
                retryable=True,
            ) from error
        except httpx.RequestError as error:
            raise StockDataError(
                StockErrorCategory.NETWORK,
                self.name,
                retryable=True,
            ) from error

        try:
            payload = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise self._invalid_response() from error
        if not isinstance(payload, dict):
            raise self._invalid_response()
        return payload

    def _invalid_response(self) -> StockDataError:
        """Return a consistent safe invalid-response error."""

        return StockDataError(
            StockErrorCategory.INVALID_RESPONSE,
            self.name,
            retryable=False,
        )

    def _raise_for_status(self, status_code: int) -> None:
        if 200 <= status_code < 300:
            return
        if status_code in {400, 404}:
            category = StockErrorCategory.INVALID_SYMBOL
            retryable = False
        elif status_code in {401, 403}:
            category = StockErrorCategory.AUTHENTICATION
            retryable = False
        elif status_code == 429:
            category = StockErrorCategory.RATE_LIMIT
            retryable = True
        elif status_code >= 500:
            category = StockErrorCategory.UNAVAILABLE
            retryable = True
        else:
            category = StockErrorCategory.INVALID_RESPONSE
            retryable = False
        raise StockDataError(category, self.name, retryable=retryable)

    @abstractmethod
    async def get_quote(self, symbol: str) -> StockPriceOutput:
        """Return a provider-normalized quote."""

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round((perf_counter() - started_at) * 1_000, 3)
