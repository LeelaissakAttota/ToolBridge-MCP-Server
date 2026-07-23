"""Tests for Company Information Tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from mcp_server.tools.finance import CompanyInfoTool
from mcp_server.tools.finance.advanced_schemas import (
    COMPANY_INFO_INPUT_SCHEMA,
    COMPANY_INFO_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import FinanceService, SymbolNotFoundError, FinanceServiceError


class TestCompanyInfoTool:
    """Test Company Information Tool."""

    @pytest.fixture
    def finance_service(self):
        """Create mock finance service."""
        return MagicMock(spec=FinanceService)

    @pytest.fixture
    def tool(self, finance_service):
        """Create tool instance with mock service."""
        tool = CompanyInfoTool(finance_service=finance_service)
        return tool

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema == COMPANY_INFO_INPUT_SCHEMA
        assert "symbol" in schema["properties"]
        assert "include_financials" in schema["properties"]
        assert "include_leadership" in schema["properties"]
        assert "include_statistics" in schema["properties"]

    def test_output_schema(self, tool):
        """Test output schema structure."""
        schema = tool.get_output_schema()
        assert schema == COMPANY_INFO_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_execute_basic(self, tool, finance_service):
        """Test basic company info execution."""
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "website": "https://www.apple.com",
            "headquarters": {
                "address": "One Apple Park Way",
                "city": "Cupertino",
                "state": "CA",
                "country": "USA",
                "zip_code": "95014",
            },
            "leadership": {
                "ceo": "Tim Cook",
                "cfo": "Luca Maestri",
                "coo": "Jeff Williams",
                "cto": "John Giannandrea",
                "board_members": ["Arthur Levinson", "Al Gore", "James Bell"],
            },
            "financials": {
                "market_cap": 3000000000000,
                "enterprise_value": 2950000000000,
                "pe_ratio": 28.5,
                "forward_pe": 25.0,
                "peg_ratio": 1.8,
                "price_to_book": 45.0,
                "price_to_sales": 7.5,
                "revenue_ttm": 383000000000,
                "gross_profit_ttm": 169000000000,
                "ebitda_ttm": 130000000000,
                "net_income_ttm": 97000000000,
                "eps_ttm": 6.10,
                "dividend_rate": 0.96,
                "dividend_yield": 0.005,
                "payout_ratio": 0.16,
                "beta": 1.25,
                "shares_outstanding": 15500000000,
                "float_shares": 15400000000,
            },
            "key_statistics": {
                "52_week_high": 199.62,
                "52_week_low": 124.17,
                "50_day_average": 185.0,
                "200_day_average": 175.0,
                "avg_volume": 55000000,
                "profit_margins": 0.25,
                "operating_margins": 0.30,
                "return_on_assets": 0.20,
                "return_on_equity": 1.47,
                "revenue_growth": 0.02,
                "earnings_growth": 0.11,
            },
            "dividends": {
                "dividend_rate": 0.96,
                "dividend_yield": 0.005,
                "ex_dividend_date": "2024-02-09",
                "payout_ratio": 0.16,
                "last_dividend_date": "2024-02-09",
                "next_dividend_date": "2024-05-10",
            },
            "splits": {
                "last_split_date": "2020-08-31",
                "last_split_ratio": "4:1",
            },
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({"symbol": "AAPL"})

        assert result["symbol"] == "AAPL"
        assert result["company_name"] == "Apple Inc."
        assert result["sector"] == "Technology"
        assert result["industry"] == "Consumer Electronics"
        assert result["financials"]["pe_ratio"] == 28.5
        assert result["financials"]["dividend_yield"] == 0.005
        assert result["financials"]["beta"] == 1.25
        assert result["financials"]["market_cap"] == 3000000000000
        assert "ceo" in result["leadership"]
        assert result["leadership"]["ceo"] == "Tim Cook"

    @pytest.mark.asyncio
    async def test_execute_without_financials(self, tool, finance_service):
        """Test execution without financials."""
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "AAPL",
            "include_financials": False,
        })

        assert "financials" not in result

    @pytest.mark.asyncio
    async def test_execute_without_leadership(self, tool, finance_service):
        """Test execution without leadership."""
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "financials": {"market_cap": 3000000000000},
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({
            "symbol": "AAPL",
            "include_leadership": False,
        })

        assert "leadership" not in result

    @pytest.mark.asyncio
    async def test_execute_invalid_symbol(self, tool, finance_service):
        """Test execution with invalid symbol."""
        finance_service.get_company_info = AsyncMock(side_effect=SymbolNotFoundError("INVALID", "yahoo_finance"))

        with pytest.raises(SymbolNotFoundError):
            await tool.execute({"symbol": "INVALID"})

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, finance_service):
        """Test execution with service error."""
        finance_service.get_company_info = AsyncMock(side_effect=FinanceServiceError("Service unavailable"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"symbol": "AAPL"})

    def test_tool_metadata(self, tool):
        """Test tool metadata."""
        assert tool.name == "company_info"
        assert "company" in tool.description.lower()
        assert "finance" in tool.tags
        assert tool.version == "1.0.0"
        assert tool.author == "ToolBridge"

    @pytest.mark.asyncio
    async def test_execute_with_52_week_high_low(self, tool, finance_service):
        """Test 52-week high/low data."""
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "TSLA",
            "company_name": "Tesla Inc.",
            "key_statistics": {
                "52_week_high": 299.29,
                "52_week_low": 101.81,
                "50_day_average": 180.0,
                "200_day_average": 220.0,
            },
            "source": "yahoo_finance",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        result = await tool.execute({"symbol": "TSLA"})

        assert result["key_statistics"]["52_week_high"] == 299.29
        assert result["key_statistics"]["52_week_low"] == 101.81