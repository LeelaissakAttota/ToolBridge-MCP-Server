"""Frankfurter exchange-rate adapter with normalized safe failures."""

import json
from datetime import date

import httpx

from toolbridge.tools.application.phase5_ports import ExchangeRateProvider
from toolbridge.tools.domain.currency import CurrencyProviderName, CurrencyRateSet
from toolbridge.tools.domain.tool_errors import ExternalDataError, ExternalErrorCategory


class FrankfurterExchangeRateProvider(ExchangeRateProvider):
    """Retrieve base-unit rates from a configured Frankfurter-compatible API."""

    def __init__(
        self,
        *,
        base_url: str,
        latest_path: str,
        timeout_seconds: float,
        max_response_bytes: int,
        user_agent: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._latest_path = latest_path
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_response_bytes = max_response_bytes
        self._user_agent = user_agent
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> CurrencyProviderName:
        """Return the stable provider name."""

        return CurrencyProviderName.FRANKFURTER

    async def initialize(self) -> None:
        """Create the provider client without making a request."""

        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                follow_redirects=False,
                transport=self._transport,
                headers={"User-Agent": self._user_agent},
            )

    async def get_rates(
        self,
        base_currency: str,
        target_currencies: tuple[str, ...],
    ) -> CurrencyRateSet:
        """Return validated rates for all requested currencies."""

        if self._client is None:
            raise ExternalDataError(ExternalErrorCategory.UNAVAILABLE, retryable=True)
        try:
            async with self._client.stream(
                "GET",
                self._latest_path,
                params={"from": base_currency, "to": ",".join(target_currencies)},
            ) as response:
                self._validate_status(response.status_code)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > self._max_response_bytes:
                        raise ExternalDataError(
                            ExternalErrorCategory.INVALID_RESPONSE,
                            retryable=False,
                        )
        except httpx.TimeoutException as error:
            raise ExternalDataError(ExternalErrorCategory.TIMEOUT, retryable=True) from error
        except httpx.RequestError as error:
            raise ExternalDataError(ExternalErrorCategory.NETWORK, retryable=True) from error
        try:
            payload = json.loads(bytes(body))
            rates_payload = payload["rates"]
            reported_base = str(payload["base"]).upper()
            if reported_base != base_currency or not isinstance(rates_payload, dict):
                raise ValueError("provider response does not match the request")
            rates = {currency: float(rates_payload[currency]) for currency in target_currencies}
            return CurrencyRateSet(
                base_currency=reported_base,
                rates=rates,
                rate_date=date.fromisoformat(str(payload["date"])),
                provider=self.name,
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ExternalDataError(
                ExternalErrorCategory.INVALID_RESPONSE,
                retryable=False,
            ) from error

    async def close(self) -> None:
        """Close the provider client idempotently."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def _validate_status(status_code: int) -> None:
        if status_code in {400, 404, 422}:
            raise ExternalDataError(ExternalErrorCategory.INVALID_INPUT, retryable=False)
        if status_code in {401, 403}:
            raise ExternalDataError(ExternalErrorCategory.AUTHENTICATION, retryable=False)
        if status_code == 429:
            raise ExternalDataError(ExternalErrorCategory.RATE_LIMIT, retryable=True)
        if 300 <= status_code < 400:
            raise ExternalDataError(ExternalErrorCategory.INVALID_RESPONSE, retryable=False)
        if status_code >= 500:
            raise ExternalDataError(ExternalErrorCategory.UNAVAILABLE, retryable=True)
        if status_code >= 400:
            raise ExternalDataError(ExternalErrorCategory.INVALID_RESPONSE, retryable=False)
