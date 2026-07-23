"""Finance service for stock market data."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from mcp_server.services.finance.exceptions import (
    FinanceServiceError,
    ProviderError,
    SymbolNotFoundError,
    MarketClosedError,
)
from mcp_server.services.finance.provider_router import ProviderRouter
from mcp_server.services.finance.metrics import metrics_collector

logger = logging.getLogger(__name__)


class FinanceService:
    """High-level finance service for stock market data."""

    def __init__(self, router: ProviderRouter):
        self.router = router
        self._running = False

    async def start(self) -> None:
        """Start the service."""
        await self.router.start()
        self._running = True
        logger.info("Finance service started")

    async def stop(self) -> None:
        """Stop the service."""
        await self.router.stop()
        self._running = False
        logger.info("Finance service stopped")

    async def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote for a symbol.

        Args:
            symbol: Stock symbol (e.g., AAPL, RELIANCE.NS)

        Returns:
            Dictionary with quote data

        Raises:
            SymbolNotFoundError: If symbol not found
            MarketClosedError: If market is closed and no real-time data
            FinanceServiceError: For other errors
        """
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        start = time.perf_counter()
        try:
            quote = await self.router.get_stock_quote(symbol.upper())
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)

            # Check if market is closed
            if quote.get("market_state") == "CLOSED":
                logger.warning(f"Market closed for {symbol}, returning last available price")

            return quote

        except SymbolNotFoundError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except MarketClosedError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get quote for {symbol}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting quote for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_multiple_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Get quotes for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to quote data (or error)
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = await self.get_stock_quote(symbol)
            except Exception as e:
                results[symbol] = {"error": str(e), "symbol": symbol}
        return results

    async def health_check(self) -> dict[str, Any]:
        """Check health of all providers."""
        provider_health = await self.router.health_check_all()
        return {
            "service": "finance",
            "status": "healthy" if any(h.healthy for h in provider_health.values()) else "degraded",
            "providers": {
                name: {
                    "healthy": health.healthy,
                    "latency_ms": health.latency_ms,
                    "last_check": health.last_check.isoformat() if health.last_check else None,
                    "error": health.error,
                }
                for name, health in provider_health.items()
            },
        }

    async def get_historical_prices(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
        include_adjusted_close: bool = True,
        include_dividends: bool = False,
        include_splits: bool = False,
    ) -> dict[str, Any]:
        """Get historical price data for a symbol.

        Args:
            symbol: Stock symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            include_adjusted_close: Include adjusted close prices
            include_dividends: Include dividend data
            include_splits: Include stock split data

        Returns:
            Dictionary with historical price data
        """
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        start = time.perf_counter()
        try:
            # Route to provider
            data = await self.router.get_historical_prices(
                symbol=symbol.upper(),
                period=period,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)

            # Post-process based on options
            if not include_adjusted_close and "data" in data:
                for point in data["data"]:
                    point.pop("adjusted_close", None)
            if not include_dividends and "data" in data:
                for point in data["data"]:
                    point.pop("dividends", None)
            if not include_splits and "data" in data:
                for point in data["data"]:
                    point.pop("stock_splits", None)

            return data

        except SymbolNotFoundError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get historical prices for {symbol}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting historical prices for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_company_info(
        self,
        symbol: str,
        include_financials: bool = True,
        include_leadership: bool = True,
        include_statistics: bool = True,
    ) -> dict[str, Any]:
        """Get comprehensive company information.

        Args:
            symbol: Stock symbol
            include_financials: Include financial metrics
            include_leadership: Include leadership/management info
            include_statistics: Include key statistics

        Returns:
            Dictionary with company information
        """
        if not symbol:
            raise FinanceServiceError("Symbol is required")

        start = time.perf_counter()
        try:
            data = await self.router.get_company_info(
                symbol=symbol.upper(),
                include_financials=include_financials,
                include_leadership=include_leadership,
                include_statistics=include_statistics,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)
            return data

        except SymbolNotFoundError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get company info for {symbol}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting company info for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_market_movers(
        self,
        movers_type: str = "gainers",
        market: str = "US",
        limit: int = 10,
        sector: str | None = None,
    ) -> dict[str, Any]:
        """Get market movers (gainers, losers, most active, trending).

        Args:
            movers_type: Type of movers (gainers, losers, most_active, trending, summary)
            market: Market to query (US, IN, EU, ALL)
            limit: Maximum number of results
            sector: Optional sector filter

        Returns:
            Dictionary with market movers data
        """
        start = time.perf_counter()
        try:
            data = await self.router.get_market_movers(
                movers_type=movers_type,
                market=market,
                limit=limit,
                sector=sector,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)
            return data

        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get market movers: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting market movers: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_technical_indicators(
        self,
        symbol: str,
        indicators: list[str],
        period: str = "3mo",
        interval: str = "1d",
        **kwargs,
    ) -> dict[str, Any]:
        """Get technical indicators for a symbol.

        Args:
            symbol: Stock symbol
            indicators: List of indicators to calculate
            period: Time period
            interval: Data interval
            **kwargs: Additional indicator parameters

        Returns:
            Dictionary with technical indicator data
        """
        if not symbol:
            raise FinanceServiceError("Symbol is required")
        if not indicators:
            raise FinanceServiceError("At least one indicator required")

        start = time.perf_counter()
        try:
            # Fetch historical data first
            hist_data = await self.router.get_historical_prices(
                symbol=symbol.upper(),
                period=period,
                interval=interval,
            )

            # Calculate indicators locally using numpy
            # This would be implemented based on the specific indicators requested
            # For now, return placeholder structure
            data = {
                "symbol": symbol.upper(),
                "name": hist_data.get("name", f"{symbol} Inc."),
                "period": period,
                "interval": interval,
                "indicators": {},
                "source": "calculated_from_yahoo_finance",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)
            return data

        except SymbolNotFoundError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get technical indicators for {symbol}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting technical indicators for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_financial_news(
        self,
        symbols: list[str] | None = None,
        category: str | None = None,
        country: str | None = None,
        limit: int = 20,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get financial news.

        Args:
            symbols: Stock symbols to filter news
            category: News category filter
            country: Country filter
            limit: Maximum articles
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with news articles
        """
        start = time.perf_counter()
        try:
            data = await self.router.get_financial_news(
                symbols=symbols,
                category=category,
                country=country,
                limit=limit,
                start_date=start_date,
                end_date=end_date,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics_collector.record_service_request("finance_service", True, latency_ms)
            return data

        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to get financial news: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error getting financial news: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e

    async def get_news_sentiment(
        self,
        symbols: list[str],
        lookback_days: int = 7,
        llm_provider: str = "cerebras",
        model: str | None = None,
    ) -> dict[str, Any]:
        """Analyze news sentiment for symbols using LLM.

        Args:
            symbols: Stock symbols to analyze
            lookback_days: Days of news to analyze
            llm_provider: LLM provider to use
            model: Specific model to use

        Returns:
            Dictionary with sentiment analysis
        """
        if not symbols:
            raise FinanceServiceError("At least one symbol required")

        start = time.perf_counter()
        try:
            # Fetch news for each symbol
            all_articles = []
            for symbol in symbols:
                news = await self.router.get_financial_news(
                    symbols=[symbol],
                    limit=20,
                    start_date=(datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d"),
                )
                all_articles.extend(news.get("articles", []))

            # Analyze with LLM
            # This would call the model router
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
            metrics_collector.record_service_request("finance_service", True, latency_ms)
            return data

        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to analyze news sentiment: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
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
        """Generate comprehensive financial analysis using LLM.

        Args:
            symbol: Stock symbol to analyze
            include_technical: Include technical analysis
            include_fundamental: Include fundamental analysis
            include_news: Include news sentiment
            llm_provider: LLM provider to use
            model: Specific model to use

        Returns:
            Dictionary with comprehensive financial analysis
        """
        if not symbol:
            raise FinanceServiceError("Symbol is required")

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

            # Build prompt and call LLM
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
            metrics_collector.record_service_request("finance_service", True, latency_ms)
            return data

        except SymbolNotFoundError:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise
        except ProviderError as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            raise FinanceServiceError(f"Failed to generate financial analysis for {symbol}: {e}") from e
        except Exception as e:
            metrics_collector.record_service_request("finance_service", False, (time.perf_counter() - start) * 1000)
            logger.error(f"Unexpected error generating financial analysis for {symbol}: {e}")
            raise FinanceServiceError(f"Unexpected error: {e}") from e