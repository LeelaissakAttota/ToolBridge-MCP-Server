"""Tests for Market Movers Tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from mcp_server.tools.finance import MarketMoversTool
from mcp_server.tools.finance.advanced_schemas import (
    MARKET_MOVERS_INPUT_SCHEMA,
    MARKET_MOVERS_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import FinanceService, FinanceServiceError


class TestMarketMoversTool:
    """Test Market Movers Tool."""

    @pytest.fixture
    def finance_service(self):
        """Create mock finance service."""
        return MagicMock(spec=FinanceService)

    @pytest.fixture
    def tool(self, finance_service):
        """Create tool instance with mock service."""
        tool = MarketMoversTool(finance_service=finance_service)
        return tool

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema == MARKET_MOVERS_INPUT_SCHEMA
        assert "type" in schema["properties"]
        assert "market" in schema["properties"]
        assert "limit" in schema["properties"]

    def test_output_schema(self, tool):
        """Test output schema structure."""
        schema = tool.get_output_schema()
        assert schema == MARKET_MOVERS_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_execute_gainers(self, tool, finance_service):
        """Test top gainers execution."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "gainers",
            "market": "US",
            "count": 3,
            "data": [
                {"symbol": "NVDA", "name": "NVIDIA Corporation", "price": 875.50, "change": 25.30, "change_percent": 2.98, "volume": 45000000, "market_cap": 2150000000000},
                {"symbol": "AMD", "name": "Advanced Micro Devices", "price": 155.20, "change": 4.80, "change_percent": 3.19, "volume": 80000000, "market_cap": 250000000000},
                {"symbol": "TSLA", "name": "Tesla Inc.", "price": 245.80, "change": 5.60, "change_percent": 2.33, "volume": 120000000, "market_cap": 780000000000},
            ],
            "market_summary": {
                "market": "US",
                "total_stocks": 5000,
                "advancing": 2850,
                "declining": 1950,
                "unchanged": 200,
            },
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "gainers",
            "market": "US",
            "limit": 10,
        })

        assert result["type"] == "gainers"
        assert result["market"] == "US"
        assert result["count"] == 3
        assert len(result["data"]) == 3
        assert result["data"][0]["symbol"] == "NVDA"
        assert result["data"][0]["change_percent"] == 2.98

    @pytest.mark.asyncio
    async def test_execute_losers(self, tool, finance_service):
        """Test top losers execution."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "losers",
            "market": "US",
            "count": 2,
            "data": [
                {"symbol": "INTC", "name": "Intel Corporation", "price": 35.20, "change": -2.10, "change_percent": -5.63, "volume": 60000000, "market_cap": 150000000000},
                {"symbol": "BA", "name": "Boeing Company", "price": 180.50, "change": -8.90, "change_percent": -4.70, "volume": 15000000, "market_cap": 110000000000},
            ],
            "market_summary": {"market": "US", "total_stocks": 5000, "advancing": 1800, "declining": 3000, "unchanged": 200},
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "losers",
            "market": "US",
            "limit": 5,
        })

        assert result["type"] == "losers"
        assert result["count"] == 2
        assert result["data"][0]["change_percent"] < 0

    @pytest.mark.asyncio
    async def test_execute_most_active(self, tool, finance_service):
        """Test most active execution."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "most_active",
            "market": "US",
            "count": 10,
            "data": [
                {"symbol": "AAPL", "name": "Apple Inc.", "price": 185.50, "change": 1.20, "change_percent": 0.65, "volume": 85000000, "market_cap": 2900000000000},
                {"symbol": "TSLA", "name": "Tesla Inc.", "price": 245.80, "change": 5.60, "change_percent": 2.33, "volume": 120000000, "market_cap": 780000000000},
            ],
            "market_summary": {"market": "US", "total_stocks": 5000, "advancing": 2500, "declining": 2300, "unchanged": 200},
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "most_active",
            "market": "US",
            "limit": 10,
        })

        assert result["type"] == "most_active"
        assert result["data"][0]["volume"] == 85000000

    @pytest.mark.asyncio
    async def test_execute_trending(self, tool, finance_service):
        """Test trending stocks execution."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "trending",
            "market": "US",
            "count": 10,
            "data": [
                {"symbol": "SMCI", "name": "Super Micro Computer", "price": 950.00, "change": 45.00, "change_percent": 4.97, "volume": 15000000, "market_cap": 55000000000},
                {"symbol": "ARM", "name": "ARM Holdings", "price": 135.00, "change": 8.50, "change_percent": 6.71, "volume": 25000000, "market_cap": 140000000000},
            ],
            "market_summary": {"market": "US", "total_stocks": 5000, "advancing": 2600, "declining": 2200, "unchanged": 200},
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "trending",
            "market": "US",
            "limit": 10,
        })

        assert result["type"] == "trending"
        assert result["data"][0]["symbol"] == "SMCI"

    @pytest.mark.asyncio
    async def test_execute_market_summary(self, tool, finance_service):
        """Test market summary execution."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "summary",
            "market": "US",
            "count": 0,
            "data": [],
            "market_summary": {
                "market": "US",
                "index_name": "S&P 500",
                "value": 4850.0,
                "change": 15.30,
                "change_percent": 0.32,
                "market_state": "OPEN",
                "advances": 2850,
                "declines": 1950,
                "unchanged": 200,
                "new_highs": 50,
                "new_lows": 20,
            },
            "sector_performance": [
                {"sector": "Technology", "change_percent": 1.5},
                {"sector": "Healthcare", "change_percent": 0.8},
                {"sector": "Financial", "change_percent": 0.5},
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "summary",
            "market": "US",
        })

        assert result["type"] == "summary"
        assert result["market_summary"]["index_name"] == "S&P 500"
        assert result["market_summary"]["change_percent"] == 0.32
        assert len(result["sector_performance"]) == 3

    @pytest.mark.asyncio
    async def test_execute_empty_results(self, tool, finance_service):
        """Test execution with empty results."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "gainers",
            "market": "US",
            "count": 0,
            "data": [],
            "market_summary": {"market": "US", "total_stocks": 0, "advancing": 0, "declining": 0, "unchanged": 0},
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "gainers",
            "market": "US",
        })

        assert result["count"] == 0
        assert len(result["data"]) == 0

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, finance_service):
        """Test execution with service error."""
        finance_service.get_market_movers = AsyncMock(side_effect=FinanceServiceError("Service unavailable"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"type": "gainers", "market": "US"})

    @pytest.mark.asyncio
    async def test_execute_different_markets(self, tool, finance_service):
        """Test execution with different markets."""
        finance_service.get_market_movers = AsyncMock(return_value={
            "type": "gainers",
            "market": "IN",
            "count": 5,
            "data": [
                {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "price": 2500.0, "change": 50.0, "change_percent": 2.04, "volume": 5000000, "market_cap": 17000000000000},
            ],
            "market_summary": {"market": "IN", "total_stocks": 2000, "advancing": 1200, "declining": 800, "unchanged": 0},
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "type": "gainers",
            "market": "IN",
            "limit": 5,
        })

        assert result["market"] == "IN"

    def test_tool_metadata(self, tool):
        """Test tool metadata."""
        assert tool.name == "market_movers"
        assert "gainers" in tool.description.lower()
        assert "losers" in tool.description.lower()
        assert "finance" in tool.tags
        assert tool.version == "1.0.0"
        assert tool.author == "ToolBridge"