"""Enterprise Finance Service with integrated components."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from mcp_server.services.finance.cache import FinanceCache
from mcp_server.services.finance.circuit_breaker import get_circuit_registry, CircuitBreakerConfig
from mcp_server.services.finance.enterprise_cache import get_cache, init_cache, close_cache
from mcp_server.services.finance.exceptions import (
    FinanceServiceError,
    ProviderError,
    SymbolNotFoundError,
    MarketClosedError,
)
from mcp_server.services.finance.finance_provider import BaseFinanceProvider
from mcp_server.services.finance.metrics import metrics_collector
from mcp_server.services.finance.observability import (
    get_metrics,
    get_health,
    init_observability,
    close_observability,
    record_request_latency,
    record_provider_request,
    record_retry,
    record_cache_hit,
    record_cache_miss,
    record_token_usage,
    record_cost,
)
from mcp_server.services.finance.provider_router import ProviderRouter
from mcp_server.services.finance.rate_limiter import get_rate_manager

logger = logging.getLogger(__name__)


class FinanceService:
    """High-level finance service for stock market data with enterprise features."""

    def __init__(self, router: ProviderRouter):
        self.router = router
        self._running = False
        self._cache = None
        self._rate_manager = None
        self._circuit_registry = None

    async def start(self) -> None:
        """Start the service with enterprise components."""
        await self.router.start()
        self._running = True

        # Initialize enterprise cache
        self._cache = await init_cache()

        # Initialize rate limiter
        self._rate_manager = get_rate_manager()

        # Initialize circuit breakers
        self._circuit_registry = get_circuit_registry()

        # Initialize observability
        await init_observability(check_interval=30)

        logger.info("Finance service started with enterprise components")

    async def stop(self) -> None:
        """Stop the service and enterprise components."""
        await self.router.stop()
        self._running = False

        # Close enterprise components
        await close_cache()
        await close_observability()

        logger.info("Finance service stopped")

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote for a symbol with caching and circuit breaker."""
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        # Check cache first
        cache_key = f"quote:{symbol.upper()}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        circuit_name = "yahoo_finance"  # Default circuit

        try:
            # Acquire rate limit token
            rate_status = await self._rate_manager.acquire(circuit_name)
            if not rate_status.allowed:
                await asyncio.sleep(rate_status.retry_after)
                rate_status = await self._rate_manager.acquire(circuit_name)

            # Execute with circuit breaker
            circuit = self._circuit_registry.get_or_create(
                circuit_name,
                CircuitBreakerConfig(name=circuit_name)
            )

            async def _fetch():
                return await self.router.get_stock_quote(symbol.upper())

            quote = await circuit.call(_fetch)

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "yahoo_finance", "operation": "get_stock_quote"})

            record_provider_request("yahoo_finance", True)
            get_metrics().increment("finance_service_requests_total",
                                   labels={"operation": "get_stock_quote", "result": "success"})

            # Check market state
            if quote.get("market_state") == "CLOSED":
                logger.warning(f"Market closed for {symbol}, returning last available price")

            # Cache the result
            await self._cache.set(cache_key, quote, ttl=30)

            return quote

        except SymbolNotFoundError:
            get_metrics().increment("finance_service_requests_total",
                                   labels={"operation": "get_stock_quote", "result": "not_found"})
            raise
        except MarketClosedError:
            get_metrics().increment("finance_service_requests_total",
                                   labels={"operation": "get_stock_quote", "result": "market_closed"})
            raise
        except ProviderError as e:
            record_provider_request("yahoo_finance", False)
            get_metrics().increment("finance_service_requests_total",
                                   labels={"operation": "get_stock_quote", "result": "provider_error"})
            raise FinanceServiceError(f"Failed to get quote for {symbol}: {e}") from e
        except Exception as e:
            get_metrics().increment("finance_service_requests_total",
                                   labels={"operation": "get_stock_quote", "result": "error"})
            logger.error(f"Unexpected error getting quote for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_company_info(
        self,
        symbol: str,
        include_financials: bool = True,
        include_leadership: bool = False,
        include_statistics: bool = False,
    ) -> dict[str, Any]:
        """Get comprehensive company information with caching."""
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        cache_key = f"company:{symbol.upper()}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            # Use router for failover
            info = await self.router.execute_with_failover(
                lambda p: p.get_company_info(symbol.upper()),
                service_name="company_info"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "yahoo_finance", "operation": "get_company_info"})

            record_provider_request("yahoo_finance", True)

            # Cache for 1 hour
            await self._cache.set(cache_key, info, ttl=3600)

            return info

        except SymbolNotFoundError:
            raise
        except ProviderError as e:
            record_provider_request("yahoo_finance", False)
            raise FinanceServiceError(f"Failed to get company info for {symbol}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting company info for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_historical_prices(
        self,
        symbol: str,
        interval: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get historical price data with caching."""
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        cache_key = f"historical:{symbol.upper()}:{interval}:{start_date}:{end_date}:{limit}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            # Use router with appropriate provider
            data = await self.router.execute_with_failover(
                lambda p: p.get_historical_prices(symbol.upper(), interval, start_date, end_date, limit),
                service_name="historical_prices"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "yahoo_finance", "operation": "get_historical_prices"})

            record_provider_request("yahoo_finance", True)

            # Cache for 10 minutes
            await self._cache.set(cache_key, data, ttl=600)

            return data

        except SymbolNotFoundError:
            raise
        except ProviderError as e:
            raise FinanceServiceError(f"Failed to get historical prices for {symbol}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting historical prices for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_market_movers(
        self,
        mover_type: str = "gainers",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Get market movers (gainers, losers, most active)."""
        cache_key = f"movers:{mover_type}:{limit}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_market_movers(mover_type, limit),
                service_name="market_movers"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "yahoo_finance", "operation": "get_market_movers"})

            record_provider_request("yahoo_finance", True)

            # Cache for 1 minute
            await self._cache.set(cache_key, data, ttl=60)

            return data

        except ProviderError as e:
            raise FinanceServiceError(f"Failed to get market movers: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting market movers: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_technical_indicators(
        self,
        symbol: str,
        indicators: list[str],
        interval: str = "1d",
        period: int = 20,
    ) -> dict[str, Any]:
        """Get technical indicators for a symbol."""
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        cache_key = f"indicators:{symbol.upper()}:{interval}:{period}:{','.join(sorted(indicators))}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_technical_indicators(symbol.upper(), indicators, interval, period),
                service_name="technical_indicators"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "yahoo_finance", "operation": "get_technical_indicators"})

            record_provider_request("yahoo_finance", True)

            # Cache for 5 minutes
            await self._cache.set(cache_key, data, ttl=300)

            return data

        except SymbolNotFoundError:
            raise
        except ProviderError as e:
            raise FinanceServiceError(f"Failed to get technical indicators for {symbol}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting technical indicators for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_financial_news(
        self,
        symbols: list[str] | None = None,
        categories: list[str] | None = None,
        limit: int = 50,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get financial news with caching."""
        cache_key = f"news:{','.join(sorted(symbols or []))}:{','.join(sorted(categories or []))}:{limit}:{start_date}:{end_date}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_financial_news(symbols, categories, limit, start_date, end_date),
                service_name="financial_news"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "yahoo_finance", "operation": "get_financial_news"})

            record_provider_request("yahoo_finance", True)

            # Cache for 5 minutes
            await self._cache.set(cache_key, data, ttl=300)

            return data

        except ProviderError as e:
            raise FinanceServiceError(f"Failed to get financial news: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting financial news: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_news_sentiment(
        self,
        symbols: list[str],
        lookback_days: int = 7,
        llm_provider: str = "cerebras",
        model: str | None = None,
    ) -> dict[str, Any]:
        """Analyze news sentiment using LLM."""
        if not symbols:
            raise FinanceServiceError("At least one symbol required")

        cache_key = f"sentiment:{','.join(sorted(symbols))}:{lookback_days}:{llm_provider}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            # Fetch news
            all_articles = []
            for symbol in symbols:
                news = await self.router.get_financial_news(
                    symbols=[symbol],
                    limit=20,
                    start_date=(datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d"),
                )
                all_articles.extend(news.get("articles", []))

            # Analyze with LLM (placeholder - would integrate with model router)
            data = {
                "symbols_analyzed": symbols,
                "lookback_days": lookback_days,
                "llm_provider": llm_provider,
                "model": model or "default",
                "total_articles_analyzed": len(all_articles),
                "overall_sentiment": {
                    "score": 0.0,
                    "label": "neutral",
                    "confidence": 0.0,
                },
                "by_symbol": {},
                "llm_explanation": "Sentiment analysis would be performed by LLM on fetched news articles.",
                "source": f"{llm_provider}_sentiment",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": llm_provider, "operation": "get_news_sentiment"})

            record_provider_request(llm_provider, True)

            # Cache for 1 hour
            await self._cache.set(cache_key, data, ttl=3600)

            return data

        except ProviderError as e:
            raise FinanceServiceError(f"Failed to analyze news sentiment: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error analyzing news sentiment: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_financial_analysis(
        self,
        symbol: str,
        include_technical: bool = True,
        include_fundamental: bool = True,
        include_news: bool = True,
        llm_provider: str = "cerebras",
        model: str | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive financial analysis using LLM."""
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        cache_key = f"analysis:{symbol.upper()}:{include_technical}:{include_fundamental}:{include_news}:{llm_provider}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            # Fetch all required data
            quote = await self.get_stock_quote(symbol)
            company = await self.get_company_info(symbol)

            technical = {}
            if include_technical:
                technical = await self.get_technical_indicators(
                    symbol=symbol,
                    indicators=["sma", "ema", "rsi", "macd", "bollinger_bands", "support_resistance", "trend"],
                )

            news_sentiment = {}
            if include_news:
                news_sentiment = await self.get_news_sentiment([symbol])

            # Build prompt and call LLM (placeholder)
            data = {
                "symbol": symbol.upper(),
                "company_name": company.get("name", symbol),
                "current_price": quote.get("current_price"),
                "currency": quote.get("currency", "USD"),
                "llm_provider": llm_provider,
                "model": model or "default",
                "executive_summary": "Comprehensive analysis would be generated by LLM based on all data sources.",
                "technical_analysis": {
                    "trend": "uptrend",
                    "trend_strength": 0.75,
                    "key_indicators": {},
                    "support_levels": [],
                    "resistance_levels": [],
                    "key_crossovers": [],
                },
                "fundamental_analysis": {
                    "valuation": "fair",
                    "financial_health": "strong",
                    "growth_prospects": "moderate",
                    "key_ratios": {},
                    "growth_drivers": [],
                    "concerns": [],
                },
                "news_sentiment": {
                    "overall_score": 0.0,
                    "label": "neutral",
                    "confidence": 0.0,
                    "key_themes": [],
                },
                "strengths": [],
                "weaknesses": [],
                "risk_factors": [],
                "growth_drivers": [],
                "investment_outlook": "hold",
                "overall_rating": 5,
                "confidence_score": 0.5,
                "key_recommendations": [],
                "source": f"yahoo_finance + {llm_provider}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": llm_provider, "operation": "get_financial_analysis"})

            record_provider_request(llm_provider, True)

            # Cache for 1 hour
            await self._cache.set(cache_key, data, ttl=3600)

            return data

        except SymbolNotFoundError:
            raise
        except ProviderError as e:
            raise FinanceServiceError(f"Failed to generate financial analysis for {symbol}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating financial analysis for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_currency_exchange(
        self,
        from_currency: str,
        to_currency: str,
        amount: float = 1.0,
    ) -> dict[str, Any]:
        """Get currency exchange rate."""
        cache_key = f"fx:{from_currency.upper()}:{to_currency.upper()}:{amount}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_exchange_rate(from_currency.upper(), to_currency.upper(), amount),
                service_name="currency_exchange"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "frankfurter", "operation": "get_currency_exchange"})

            record_provider_request("frankfurter", True)

            # Cache for 5 minutes
            await self._cache.set(cache_key, data, ttl=300)

            return data

        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            raise FinanceServiceError(f"Failed to get exchange rate: {e}") from e

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        """Get list of supported currencies."""
        cache_key = "currencies:all"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("finance_service")
            return cached

        record_cache_miss("finance_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_supported_currencies(),
                service_name="supported_currencies"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("finance_request_latency_ms", latency_ms,
                                   labels={"provider": "frankfurter", "operation": "get_supported_currencies"})

            record_provider_request("frankfurter", True)

            # Cache for 24 hours
            await self._cache.set(cache_key, data, ttl=86400)

            return data

        except Exception as e:
            logger.error(f"Error getting supported currencies: {e}")
            raise FinanceServiceError(f"Failed to get supported currencies: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Comprehensive health check."""
        provider_status = await self.router.get_provider_status()
        cache_stats = await self._cache.get_stats_async() if self._cache else {}

        return {
            "service": "finance",
            "status": "healthy" if self._running else "stopped",
            "running": self._running,
            "providers": provider_status,
            "cache": cache_stats,
            "circuit_breakers": {
                name: breaker.get_status()
                for name, breaker in self._circuit_registry._breakers.items()
            } if self._circuit_registry else {},
            "rate_limiters": self._rate_manager.get_all_status() if self._rate_manager else {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class CurrencyService:
    """Enterprise Currency Service with integrated components."""

    def __init__(self, router: ProviderRouter):
        self.router = router
        self._running = False
        self._cache = None
        self._rate_manager = None

    async def start(self) -> None:
        """Start the service."""
        await self.router.start()
        self._running = True
        self._cache = await get_global_cache()
        self._rate_manager = get_rate_manager()
        logger.info("Currency service started")

    async def stop(self) -> None:
        """Stop the service."""
        await self.router.stop()
        self._running = False
        logger.info("Currency service stopped")

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        amount: float = 1.0,
    ) -> dict[str, Any]:
        """Get currency exchange rate."""
        cache_key = f"fx:{from_currency.upper()}:{to_currency.upper()}:{amount}"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("currency_service")
            return cached

        record_cache_miss("currency_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_exchange_rate(from_currency.upper(), to_currency.upper(), amount),
                service_name="currency_exchange"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("currency_request_latency_ms", latency_ms,
                                   labels={"provider": "frankfurter", "operation": "get_exchange_rate"})

            record_provider_request("frankfurter", True)

            # Cache for 5 minutes
            await self._cache.set(f"fx:{from_currency.upper()}:{to_currency.upper()}:{amount}", data, ttl=300)

            return data

        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            raise FinanceServiceError(f"Failed to get exchange rate: {e}") from e

    async def get_supported_currencies(self) -> list[dict[str, Any]]:
        """Get supported currencies."""
        cache_key = "currencies:all"
        cached = await self._cache.get(cache_key)
        if cached:
            record_cache_hit("currency_service")
            return cached

        record_cache_miss("currency_service")

        start = time.perf_counter()
        try:
            data = await self.router.execute_with_failover(
                lambda p: p.get_supported_currencies(),
                service_name="supported_currencies"
            )

            latency_ms = (time.perf_counter() - start) * 1000
            get_metrics().histogram("currency_request_latency_ms", latency_ms,
                                   labels={"provider": "frankfurter", "operation": "get_supported_currencies"})

            record_provider_request("frankfurter", True)

            # Cache for 24 hours
            await self._cache.set(cache_key, data, ttl=86400)

            return data

        except Exception as e:
            logger.error(f"Error getting supported currencies: {e}")
            raise FinanceServiceError(f"Failed to get supported currencies: {e}") from e

    async def health_check(self) -> dict[str, Any]:
        """Health check for currency service."""
        provider_status = await self.router.get_provider_status()
        return {
            "service": "currency",
            "status": "healthy" if self._running else "stopped",
            "running": self._running,
            "providers": provider_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }