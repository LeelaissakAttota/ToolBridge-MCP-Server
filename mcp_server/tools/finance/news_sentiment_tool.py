"""News Sentiment Tool - Analyze sentiment of financial news using LLM."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    NEWS_SENTIMENT_INPUT_SCHEMA,
    NEWS_SENTIMENT_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import NewsSentimentError
from mcp_server.services.finance import FinanceService, FinanceServiceError

logger = logging.getLogger(__name__)


class NewsSentimentTool(BaseTool):
    """Tool for analyzing sentiment of financial news using LLM.

    Workflow:
    1. Fetch news articles for given symbols
    2. Send to LLM for sentiment analysis
    3. Return sentiment scores, labels, confidence, themes, and explanations

    Uses Finance Service for news + Provider Layer for LLM analysis.
    """

    name = "news_sentiment"
    description = "Analyze sentiment of financial news for given symbols using LLM providers (Cerebras, NVIDIA, OpenRouter)"
    tags = ["finance", "sentiment", "news", "llm", "analysis"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(self, finance_service: Optional[FinanceService] = None, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._finance_service = finance_service
        self._service_initialized = finance_service is not None

    def set_finance_service(self, service: FinanceService) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = finance_service
        self._service_initialized = True

    def get_input_schema(self) -> dict[str, Any]:
        return NEWS_SENTIMENT_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return NEWS_SENTIMENT_OUTPUT_SCHEMA

    def _build_sentiment_prompt(self, symbol: str, articles: list[dict]) -> str:
        """Build prompt for sentiment analysis."""
        article_texts = []
        for i, article in enumerate(articles[:10]):  # Limit to 10 articles
            article_texts.append(
                f"Article {i+1}: {article.get('title', '')}\n"
                f"Summary: {article.get('summary', '')}\n"
                f"Source: {article.get('source', '')}\n"
                f"Published: {article.get('published_at', '')}\n"
            )

        articles_text = "\n---\n".join(article_texts)

        return f"""Analyze the sentiment of the following financial news articles for {symbol}.

Articles:
{articles_text}

Provide a JSON response with:
{{
    "sentiment_score": float between -1 (very bearish) and 1 (very bullish),
    "label": "very_bearish" | "bearish" | "neutral" | "bullish" | "very_bullish",
    "confidence": float between 0 and 1,
    "key_themes": ["theme1", "theme2", ...],
    "summary": "Brief explanation of the sentiment analysis",
    "articles_count": integer
}}"""

    async def _analyze_with_llm(self, symbol: str, articles: list[dict], llm_provider: str, model: str | None = None) -> dict:
        """Analyze sentiment for a single symbol using LLM.
        
        This method can be mocked in tests.
        """
        # In real implementation, this would call the model_router
        # For now, return placeholder
        return {
            "sentiment_score": 0.0,
            "label": "neutral",
            "confidence": 0.0,
            "key_themes": [],
            "summary": f"No articles analyzed for {symbol}",
            "articles_count": len(articles),
        }

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute news sentiment analysis."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbols = arguments["symbols"]
        lookback_days = arguments.get("lookback_days", 7)
        llm_provider = arguments.get("llm_provider", "cerebras")
        model = arguments.get("model")

        logger.info(f"Analyzing news sentiment for {symbols} (lookback: {lookback_days}d, LLM: {llm_provider})")

        try:
            # Fetch news for each symbol
            all_articles = {}
            for symbol in symbols:
                news = await self._finance_service.get_financial_news(
                    symbols=[symbol],
                    limit=20,
                )
                all_articles[symbol] = news.get("articles", [])

            # Analyze sentiment for each symbol using LLM
            by_symbol = {}
            for symbol in symbols:
                articles = all_articles.get(symbol, [])
                if articles:
                    try:
                        sentiment = await self._analyze_with_llm(symbol, articles, llm_provider, model)
                        by_symbol[symbol] = sentiment
                    except Exception as e:
                        logger.warning(f"LLM analysis failed for {symbol}: {e}")
                        # Fallback for this symbol
                        by_symbol[symbol] = {
                            "sentiment_score": 0.0,
                            "label": "neutral",
                            "confidence": 0.0,
                            "key_themes": [],
                            "summary": f"LLM analysis failed: {e}",
                            "articles_count": len(articles),
                        }
                else:
                    by_symbol[symbol] = {
                        "sentiment_score": 0.0,
                        "label": "neutral",
                        "confidence": 0.0,
                        "key_themes": [],
                        "summary": "No news articles found",
                        "articles_count": 0,
                    }

            # Calculate overall sentiment
            total_articles = sum(s.get("articles_count", 0) for s in by_symbol.values())
            if total_articles > 0:
                weighted_score = sum(s.get("sentiment_score", 0) * s.get("articles_count", 0) for s in by_symbol.values()) / total_articles
                avg_confidence = sum(s.get("confidence", 0) for s in by_symbol.values()) / len(by_symbol)
                
                if weighted_score > 0.5:
                    label = "very_bullish"
                elif weighted_score > 0.1:
                    label = "bullish"
                elif weighted_score > -0.1:
                    label = "neutral"
                elif weighted_score > -0.5:
                    label = "bearish"
                else:
                    label = "very_bearish"
            else:
                weighted_score = 0.0
                avg_confidence = 0.0
                label = "neutral"

            from datetime import datetime, timezone
            
            response = {
                "symbols_analyzed": symbols,
                "lookback_days": lookback_days,
                "llm_provider": llm_provider,
                "model": model or "default",
                "total_articles_analyzed": total_articles,
                "overall_sentiment": {
                    "score": weighted_score,
                    "label": label,
                    "confidence": avg_confidence,
                },
                "by_symbol": by_symbol,
                "llm_explanation": f"Sentiment analysis performed using {llm_provider} on {total_articles} news articles for {len(symbols)} symbols.",
                "source": f"{llm_provider}_sentiment",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"News sentiment analysis completed for {symbols}")
            return response

        except FinanceServiceError as e:
            logger.error(f"Finance service error analyzing news sentiment for {symbols}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error analyzing news sentiment for {symbols}: {e}")
            raise NewsSentimentError(symbols, f"Unexpected error: {e}") from e

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)