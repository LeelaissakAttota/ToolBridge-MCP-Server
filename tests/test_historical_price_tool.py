"""Tests for Historical Price Tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from mcp_server.tools.finance import HistoricalPriceTool
from mcp_server.tools.finance.advanced_schemas import (
    HISTORICAL_PRICE_INPUT_SCHEMA,
    HISTORICAL_PRICE_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import FinanceService, SymbolNotFoundError, FinanceServiceError


class TestHistoricalPriceTool:
    """Test Historical Price Tool."""

    @pytest.fixture
    def finance_service(self):
        """Create mock finance service."""
        return MagicMock(spec=FinanceService)

    @pytest.fixture
    def tool(self, finance_service):
        """Create tool instance with mock service."""
        tool = HistoricalPriceTool(finance_service=finance_service)
        return tool

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema == HISTORICAL_PRICE_INPUT_SCHEMA
        assert "symbol" in schema["properties"]
        assert "period" in schema["properties"]
        assert "interval" in schema["properties"]
        assert "start_date" in schema["properties"]
        assert "end_date" in schema["properties"]

    def test_output_schema(self, tool):
        """Test output schema structure."""
        schema = tool.get_output_schema()
        assert schema == HISTORICAL_PRICE_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_execute_basic(self, tool, finance_service):
        """Test basic historical price execution."""
        finance_service.get_historical_prices = AsyncMock(return_value={
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "currency": "USD",
            "exchange": "NASDAQ",
            "period": "1mo",
            "interval": "1d",
            "data_points": 20,
            "data": [
                {
                    "date": "2024-01-01T00:00:00Z",
                    "open": 185.0,
                    "high": 188.0,
                    "low": 184.0,
                    "close": 187.5,
                    "adjusted_close": 187.5,
                    "volume": 50000000,
                }
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "AAPL",
            "period": "1mo",
            "interval": "1d",
        })

        assert result["symbol"] == "AAPL"
        assert result["period"] == "1mo"
        assert result["interval"] == "1d"
        assert len(result["data"]) == 1
        assert result["data"][0]["close"] == 187.5

    @pytest.mark.asyncio
    async def test_execute_with_date_range(self, tool, finance_service):
        """Test execution with custom date range."""
        finance_service.get_historical_prices = AsyncMock(return_value={
            "symbol": "MSFT",
            "data": [
                {"date": "2024-01-01T00:00:00Z", "open": 370, "high": 375, "low": 368, "close": 372, "volume": 30000000},
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "MSFT",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "interval": "1d",
        })

        assert result["symbol"] == "MSFT"

    @pytest.mark.asyncio
    async def test_execute_invalid_symbol(self, tool, finance_service):
        """Test execution with invalid symbol."""
        finance_service.get_historical_prices = AsyncMock(side_effect=SymbolNotFoundError("INVALID", "yahoo_finance"))

        with pytest.raises(SymbolNotFoundError):
            await tool.execute({"symbol": "INVALID"})

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, finance_service):
        """Test execution with service error."""
        finance_service.get_historical_prices = AsyncMock(side_effect=FinanceServiceError("Service unavailable"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"symbol": "AAPL"})

    def test_tool_metadata(self, tool):
        """Test tool metadata."""
        assert tool.name == "historical_price"
        assert "historical" in tool.description.lower()
        assert "finance" in tool.tags
        assert tool.version == "1.0.0"
        assert tool.author == "ToolBridge"

    @pytest.mark.asyncio
    async def test_execute_with_adjusted_close(self, tool, finance_service):
        """Test execution with adjusted close option."""
        finance_service.get_historical_prices = AsyncMock(return_value={
            "symbol": "AAPL",
            "data": [
                {
                    "date": "2024-01-01T00:00:00Z",
                    "open": 185.0,
                    "high": 188.0,
                    "low": 184.0,
                    "close": 187.5,
                    "adjusted_close": 187.0,  # Adjusted for split/dividend
                    "volume": 50000000,
                    "dividends": 0.0,
                    "stock_splits": 0.0,
                }
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "AAPL",
            "include_adjusted_close": True,
            "include_dividends": True,
            "include_splits": True,
        })

        assert result["data"][0]["adjusted_close"] == 187.0

    @pytest.mark.asyncio
    async def test_execute_weekly_interval(self, tool, finance_service):
        """Test execution with weekly interval."""
        finance_service.get_historical_prices = AsyncMock(return_value={
            "symbol": "AAPL",
            "period": "3mo",
            "interval": "1wk",
            "data": [
                {"date": "2024-01-01T00:00:00Z", "open": 180, "high": 190, "low": 178, "close": 185, "volume": 200000000},
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "AAPL",
            "period": "3mo",
            "interval": "1wk",
        })

        assert result["interval"] == "1wk"

    @pytest.mark.asyncio
    async def test_execute_monthly_interval(self, tool, finance_service):
        """Test execution with monthly interval."""
        finance_service.get_historical_prices = AsyncMock(return_value={
            "symbol": "AAPL",
            "period": "1y",
            "interval": "1mo",
            "data": [
                {"date": "2024-01-01T00:00:00Z", "open": 170, "high": 195, "low": 165, "close": 185, "volume": 800000000},
            ],
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "AAPL",
            "period": "1y",
            "interval": "1mo",
        })

        assert result["interval"] == "1mo"