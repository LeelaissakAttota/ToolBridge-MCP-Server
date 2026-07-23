"""Tests for Financial News Tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from mcp_server.tools.finance import FinancialNewsTool
from mcp_server.tools.finance.advanced_schemas import (
    FINANCIAL_NEWS_INPUT_SCHEMA,
    FINANCIAL_NEWS_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import FinanceService, FinanceServiceError


class TestFinancialNewsTool:
    """Test Financial News Tool."""

    @pytest.fixture
    def finance_service(self):
        """Create mock finance service."""
        return MagicMock(spec=FinanceService)

    @pytest.fixture
    def tool(self, finance_service):
        """Create tool instance with mock service."""
        tool = FinancialNewsTool(finance_service=finance_service)
        return tool

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema == FINANCIAL_NEWS_INPUT_SCHEMA
        assert "symbols" in schema["properties"]
        assert "category" in schema["properties"]
        assert "country" in schema["properties"]
        assert "limit" in schema["properties"]
        assert "start_date" in schema["properties"]
        assert "end_date" in schema["properties"]

    def test_output_schema(self, tool):
        """Test output schema structure."""
        schema = tool.get_output_schema()
        assert schema == FINANCIAL_NEWS_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_execute_company_news(self, tool, finance_service):
        """Test company news execution."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 2,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Apple Reports Strong Q4 Earnings",
                    "summary": "Apple exceeded analyst expectations with record iPhone sales.",
                    "url": "https://finance.yahoo.com/news/apple-q4-earnings",
                    "source": "Yahoo Finance",
                    "category": "earnings",
                    "symbols": ["AAPL"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "image_url": "https://example.com/apple.jpg",
                },
                {
                    "id": "news_2",
                    "title": "New iPhone Launch Breaks Records",
                    "summary": "iPhone 15 pre-orders surpass all previous models.",
                    "url": "https://finance.yahoo.com/news/iphone-launch",
                    "source": "Yahoo Finance",
                    "category": "product_launch",
                    "symbols": ["AAPL"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "image_url": "https://example.com/iphone.jpg",
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbols": ["AAPL"],
            "limit": 10,
        })

        assert result["total_articles"] == 2
        assert len(result["articles"]) == 2
        assert result["articles"][0]["symbols"] == ["AAPL"]
        assert result["articles"][0]["category"] == "earnings"

    @pytest.mark.asyncio
    async def test_execute_sector_news(self, tool, finance_service):
        """Test sector news execution."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Semiconductor Sector Sees Strong Growth",
                    "summary": "Chip demand surges across AI and automotive sectors.",
                    "url": "https://finance.yahoo.com/news/semiconductor-growth",
                    "source": "Yahoo Finance",
                    "category": "sector",
                    "symbols": ["NVDA", "AMD", "INTC"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "image_url": "https://example.com/chips.jpg",
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "category": "sector",
            "limit": 10,
        })

        assert result["total_articles"] == 1
        assert result["articles"][0]["category"] == "sector"

    @pytest.mark.asyncio
    async def test_execute_market_news(self, tool, finance_service):
        """Test market news execution."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 2,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Fed Holds Interest Rates Steady",
                    "summary": "Federal Reserve maintains rates amid inflation concerns.",
                    "url": "https://finance.yahoo.com/news/fed-rates",
                    "source": "Yahoo Finance",
                    "category": "general",
                    "symbols": ["SPY", "DIA", "QQQ"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "image_url": "https://example.com/fed.jpg",
                },
                {
                    "id": "news_2",
                    "title": "Market Rally Continues",
                    "summary": "Indices reach new highs.",
                    "url": "https://finance.yahoo.com/news/market-rally",
                    "source": "Yahoo Finance",
                    "category": "general",
                    "symbols": ["SPY", "QQQ"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "category": "general",
            "limit": 10,
        })

        assert result["total_articles"] == 2
        assert "Fed" in result["articles"][0]["title"]

    @pytest.mark.asyncio
    async def test_execute_breaking_news(self, tool, finance_service):
        """Test breaking news execution."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [
                {
                    "id": "breaking_1",
                    "title": "BREAKING: Major Bank Announces Merger",
                    "summary": "Two largest regional banks agree to $50B merger.",
                    "url": "https://finance.yahoo.com/news/bank-merger",
                    "source": "Yahoo Finance",
                    "category": "mergers",
                    "symbols": ["BANK1", "BANK2"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "image_url": "https://example.com/bank.jpg",
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "category": "mergers",
            "limit": 5,
        })

        assert result["total_articles"] == 1
        assert result["articles"][0]["category"] == "mergers"

    @pytest.mark.asyncio
    async def test_execute_category_filter(self, tool, finance_service):
        """Test category filtering."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 2,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Apple Dividend Increase",
                    "summary": "Apple raises dividend by 4%.",
                    "url": "https://finance.yahoo.com/news/apple-dividend",
                    "source": "Yahoo Finance",
                    "category": "dividend",
                    "symbols": ["AAPL"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": "news_2",
                    "title": "Microsoft Dividend Announcement",
                    "summary": "Microsoft declares quarterly dividend.",
                    "url": "https://finance.yahoo.com/news/msft-dividend",
                    "source": "Yahoo Finance",
                    "category": "dividend",
                    "symbols": ["MSFT"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "category": "dividend",
            "limit": 10,
        })

        assert result["total_articles"] == 2
        assert all(a["category"] == "dividend" for a in result["articles"])

    @pytest.mark.asyncio
    async def test_execute_country_filter(self, tool, finance_service):
        """Test country filtering."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Tokyo Stock Exchange New Rules",
                    "summary": "TSE implements new corporate governance requirements.",
                    "url": "https://finance.yahoo.com/news/tse-rules",
                    "source": "Yahoo Finance",
                    "category": "regulation",
                    "symbols": ["7203.T"],
                    "published_at": datetime.now(timezone.utc).isoformat(),
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "country": "JP",
            "limit": 10,
        })

        assert result["total_articles"] == 1

    @pytest.mark.asyncio
    async def test_execute_date_filter(self, tool, finance_service):
        """Test date range filtering."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 1,
            "articles": [
                {
                    "id": "news_1",
                    "title": "Q4 Earnings Season Begins",
                    "summary": "Major banks kick off earnings season.",
                    "url": "https://finance.yahoo.com/news/earnings-season",
                    "source": "Yahoo Finance",
                    "category": "earnings",
                    "symbols": ["JPM", "BAC"],
                    "published_at": "2024-01-12T00:00:00Z",
                },
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "limit": 10,
        })

        assert result["total_articles"] == 1

    @pytest.mark.asyncio
    async def test_execute_empty_results(self, tool, finance_service):
        """Test execution with empty results."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 0,
            "articles": [],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbols": ["NONEXISTENT"],
            "limit": 10,
        })

        assert result["total_articles"] == 0
        assert len(result["articles"]) == 0

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, finance_service):
        """Test execution with service error."""
        finance_service.get_financial_news = AsyncMock(side_effect=FinanceServiceError("Service unavailable"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"symbols": ["AAPL"]})

    @pytest.mark.asyncio
    async def test_execute_limit_enforced(self, tool, finance_service):
        """Test limit parameter is enforced."""
        finance_service.get_financial_news = AsyncMock(return_value={
            "total_articles": 100,
            "articles": [
                {"id": f"news_{i}", "title": f"Article {i}", "summary": f"Summary {i}", 
                 "url": f"https://example.com/{i}", "source": "Yahoo Finance", 
                 "category": "general", "symbols": ["AAPL"], 
                 "published_at": datetime.now(timezone.utc).isoformat()}
                for i in range(100)
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "limit": 5,
        })

        assert result["total_articles"] == 100  # Total available
        assert len(result["articles"]) == 5  # But limited to 5

    def test_tool_metadata(self, tool):
        """Test tool metadata."""
        assert tool.name == "financial_news"
        assert "news" in tool.description.lower()
        assert "finance" in tool.tags
        assert tool.version == "1.0.0"
        assert tool.author == "ToolBridge"