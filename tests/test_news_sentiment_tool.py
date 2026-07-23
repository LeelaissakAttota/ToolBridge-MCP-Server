"""Tests for News Sentiment Tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from mcp_server.tools.finance import NewsSentimentTool
from mcp_server.tools.finance.advanced_schemas import (
    NEWS_SENTIMENT_INPUT_SCHEMA,
    NEWS_SENTIMENT_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import FinanceService, FinanceServiceError


class TestNewsSentimentTool:
    """Test News Sentiment Tool."""

    @pytest.fixture
    def finance_service(self):
        """Create mock finance service."""
        return MagicMock(spec=FinanceService)

    @pytest.fixture
    def tool(self, finance_service):
        """Create tool instance with mock service."""
        tool = NewsSentimentTool(finance_service=finance_service)
        return tool

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema == NEWS_SENTIMENT_INPUT_SCHEMA
        assert "symbols" in schema["properties"]
        assert "lookback_days" in schema["properties"]
        assert "llm_provider" in schema["properties"]
        assert "model" in schema["properties"]

    def test_output_schema(self, tool):
        """Test output schema structure."""
        schema = tool.get_output_schema()
        assert schema == NEWS_SENTIMENT_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_execute_positive_sentiment(self, tool, finance_service):
        """Test positive sentiment analysis."""
        # Mock news fetch
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 3,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Apple Crushes Earnings Expectations",
                    "summary": "Apple reports record revenue and profits driven by strong iPhone 15 sales.",
                    "source": "Yahoo Finance",
                    "category": "earnings",
                    "symbols": ["AAPL"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "news_2",
                    "title": "Analysts Raise Apple Price Target",
                    "summary": "Multiple analysts upgrade AAPL to Buy with higher price targets.",
                    "source": "Yahoo Finance",
                    "category": "analyst_rating",
                    "symbols": ["AAPL"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "news_3",
                    "title": "Apple Announces Major Buyback Program",
                    "summary": "Apple authorizes $100B share repurchase program.",
                    "source": "Yahoo Finance",
                    "category": "corporate_action",
                    "symbols": ["AAPL"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Mock LLM response
        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "sentiment_score": 0.85,
                "label": "very_bullish",
                "confidence": 0.92,
                "key_themes": ["Strong earnings", "Analyst upgrades", "Share buyback"],
                "summary": "Overwhelmingly positive news flow for Apple with record earnings, analyst upgrades, and significant capital return program.",
                "articles_count": 3,
            }

            result = await tool.execute({
                "symbols": ["AAPL"],
                "lookback_days": 7,
                "llm_provider": "cerebras",
            })

        assert result["symbols_analyzed"] == ["AAPL"]
        assert result["lookback_days"] == 7
        assert result["llm_provider"] == "cerebras"
        assert result["overall_sentiment"]["score"] == 0.85
        assert result["overall_sentiment"]["label"] == "very_bullish"
        assert result["overall_sentiment"]["confidence"] == 0.92
        assert "AAPL" in result["by_symbol"]
        assert result["by_symbol"]["AAPL"]["sentiment_score"] == 0.85

    @pytest.mark.asyncio
    async def test_execute_negative_sentiment(self, tool, finance_service):
        """Test negative sentiment analysis."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 3,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Company Misses Earnings Badly",
                    "summary": "Revenue falls 20% YoY, guidance slashed.",
                    "source": "Yahoo Finance",
                    "category": "earnings",
                    "symbols": ["BADCO"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "news_2",
                    "title": "CEO Resigns Amid Scandal",
                    "summary": "Leadership turmoil as CEO steps down.",
                    "source": "Yahoo Finance",
                    "category": "management_change",
                    "symbols": ["BADCO"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "news_3",
                    "title": "Regulatory Investigation Launched",
                    "summary": "SEC opens probe into accounting practices.",
                    "source": "Yahoo Finance",
                    "category": "regulation",
                    "symbols": ["BADCO"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "sentiment_score": -0.75,
                "label": "very_bearish",
                "confidence": 0.88,
                "key_themes": ["Earnings miss", "Management turmoil", "Regulatory risk"],
                "summary": "Highly negative news flow with earnings disappointment, leadership crisis, and regulatory scrutiny.",
                "articles_count": 3,
            }

            result = await tool.execute({
                "symbols": ["BADCO"],
                "lookback_days": 7,
            })

        assert result["overall_sentiment"]["score"] == -0.75
        assert result["overall_sentiment"]["label"] == "very_bearish"
        assert result["by_symbol"]["BADCO"]["label"] == "very_bearish"

    @pytest.mark.asyncio
    async def test_execute_neutral_sentiment(self, tool, finance_service):
        """Test neutral sentiment analysis."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 2,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Company Holds Annual Meeting",
                    "summary": "Routine annual shareholder meeting scheduled.",
                    "source": "Yahoo Finance",
                    "category": "corporate_action",
                    "symbols": ["NEUTCO"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "news_2",
                    "title": "Quarterly Dividend Declared",
                    "summary": "Regular quarterly dividend announced at same rate.",
                    "source": "Yahoo Finance",
                    "category": "dividend",
                    "symbols": ["NEUTCO"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "sentiment_score": 0.05,
                "label": "neutral",
                "confidence": 0.65,
                "key_themes": ["Routine operations", "No material changes"],
                "summary": "Neutral news flow with routine corporate actions and no significant catalysts.",
                "articles_count": 2,
            }

            result = await tool.execute({
                "symbols": ["NEUTCO"],
                "lookback_days": 7,
            })

        assert result["overall_sentiment"]["score"] == 0.05
        assert result["overall_sentiment"]["label"] == "neutral"
        assert result["by_symbol"]["NEUTCO"]["label"] == "neutral"

    @pytest.mark.asyncio
    async def test_execute_multiple_symbols(self, tool, finance_service):
        """Test sentiment analysis for multiple symbols."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 4,
            "articles": [
                {"id": "1", "title": "Apple Earnings Beat", "summary": "AAPL beats", "source": "YF", "category": "earnings", "symbols": ["AAPL"], "published_at": datetime.now(timezone.utc).isoformat()},
                {"id": "2", "title": "Microsoft Cloud Growth", "summary": "MSFT Azure strong", "source": "YF", "category": "earnings", "symbols": ["MSFT"], "published_at": datetime.now(timezone.utc).isoformat()},
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [
                {"sentiment_score": 0.7, "label": "bullish", "confidence": 0.85, "key_themes": ["Earnings beat"], "summary": "Positive", "articles_count": 1},
                {"sentiment_score": 0.6, "label": "bullish", "confidence": 0.8, "key_themes": ["Cloud growth"], "summary": "Positive", "articles_count": 1},
            ]

            result = await tool.execute({
                "symbols": ["AAPL", "MSFT"],
                "lookback_days": 7,
            })

        assert len(result["symbols_analyzed"]) == 2
        assert "AAPL" in result["by_symbol"]
        assert "MSFT" in result["by_symbol"]
        assert result["by_symbol"]["AAPL"]["sentiment_score"] == 0.7
        assert result["by_symbol"]["MSFT"]["sentiment_score"] == 0.6

    @pytest.mark.asyncio
    async def test_execute_confidence_score(self, tool, finance_service):
        """Test confidence score in response."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [{"id": "1", "title": "Test", "summary": "Test", "source": "YF", "category": "general", "symbols": ["AAPL"], "published_at": datetime.now(timezone.utc).isoformat()}],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "sentiment_score": 0.5,
                "label": "bullish",
                "confidence": 0.75,
                "key_themes": ["Test"],
                "summary": "Test",
                "articles_count": 1,
            }

            result = await tool.execute({"symbols": ["AAPL"]})

        assert 0 <= result["overall_sentiment"]["confidence"] <= 1
        assert 0 <= result["by_symbol"]["AAPL"]["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_execute_llm_explanation(self, tool, finance_service):
        """Test LLM explanation in response."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [{"id": "1", "title": "Test", "summary": "Test", "source": "YF", "category": "general", "symbols": ["AAPL"], "published_at": datetime.now(timezone.utc).isoformat()}],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "sentiment_score": 0.5,
                "label": "bullish",
                "confidence": 0.75,
                "key_themes": ["Test"],
                "summary": "Detailed explanation from LLM about why sentiment is bullish based on the news articles analyzed.",
                "articles_count": 1,
            }

            result = await tool.execute({"symbols": ["AAPL"]})

        assert "llm_explanation" in result
        assert len(result["llm_explanation"]) > 0

    @pytest.mark.asyncio
    async def test_execute_llm_provider_failover(self, tool, finance_service):
        """Test LLM provider failover."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [{"id": "1", "title": "Test", "summary": "Test", "source": "YF", "category": "general", "symbols": ["AAPL"], "published_at": datetime.now(timezone.utc).isoformat()}],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            # First provider fails, second succeeds
            mock_llm.side_effect = [
                Exception("Cerebras unavailable"),
                {"sentiment_score": 0.5, "label": "neutral", "confidence": 0.5, "key_themes": [], "summary": "Fallback", "articles_count": 1},
            ]

            result = await tool.execute({
                "symbols": ["AAPL"],
                "llm_provider": "cerebras",
            })

        # Should still return result (fallback handled by tool)
        assert "symbols_analyzed" in result

    @pytest.mark.asyncio
    async def test_execute_no_news(self, tool, finance_service):
        """Test sentiment with no news articles."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 0,
            "articles": [],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbols": ["UNKNOWN"],
            "lookback_days": 7,
        })

        assert result["total_articles_analyzed"] == 0
        assert result["overall_sentiment"]["label"] == "neutral"

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, finance_service):
        """Test execution with service error."""
        finance_service.get_financial_news = AsyncMock(side_effect=FinanceServiceError("Service unavailable"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"symbols": ["AAPL"]})

    def test_tool_metadata(self, tool):
        """Test tool metadata."""
        assert tool.name == "news_sentiment"
        assert "sentiment" in tool.description.lower()
        assert "llm" in tool.description.lower()
        assert "finance" in tool.tags
        assert tool.version == "1.0.0"
        assert tool.author == "ToolBridge"