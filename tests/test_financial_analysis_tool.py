"""Tests for Financial Analysis Tool."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_server.tools.finance import FinancialAnalysisTool
from mcp_server.tools.finance.advanced_schemas import (
    FINANCIAL_ANALYSIS_INPUT_SCHEMA,
    FINANCIAL_ANALYSIS_OUTPUT_SCHEMA,
)
from mcp_server.services.finance import FinanceService, CurrencyService, FinanceServiceError


class TestFinancialAnalysisTool:
    """Test Financial Analysis Tool."""

    @pytest.fixture
    def finance_service(self):
        """Create mock finance service."""
        return MagicMock(spec=FinanceService)

    @pytest.fixture
    def currency_service(self):
        """Create mock currency service."""
        return MagicMock(spec=CurrencyService)

    @pytest.fixture
    def tool(self, finance_service, currency_service):
        """Create tool instance with mock services."""
        tool = FinancialAnalysisTool(finance_service=finance_service, currency_service=currency_service)
        return tool

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.get_input_schema()
        assert schema == FINANCIAL_ANALYSIS_INPUT_SCHEMA
        assert "symbol" in schema["properties"]
        assert "include_technical" in schema["properties"]
        assert "include_fundamental" in schema["properties"]
        assert "include_news" in schema["properties"]
        assert "llm_provider" in schema["properties"]
        assert "model" in schema["properties"]

    def test_output_schema(self, tool):
        """Test output schema structure."""
        schema = tool.get_output_schema()
        assert schema == FINANCIAL_ANALYSIS_OUTPUT_SCHEMA

    @pytest.mark.asyncio
    async def test_execute_basic_analysis(self, tool, finance_service):
        """Test basic financial analysis execution."""
        # Mock quote
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 185.50,
            "change": 2.30,
            "change_percent": 1.26,
            "volume": 55000000,
            "market_state": "OPEN",
            "fifty_two_week_high": 199.62,
            "fifty_two_week_low": 124.17,
            "currency": "USD",
        })

        # Mock company info
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 3000000000000,
            "pe_ratio": 28.5,
            "forward_pe": 25.0,
            "peg_ratio": 1.8,
            "price_to_book": 45.0,
            "dividend_yield": 0.005,
            "eps": 6.10,
            "revenue": 383000000000,
            "net_income": 97000000000,
            "profit_margin": 0.25,
            "return_on_equity": 1.47,
            "debt_to_equity": 0.3,
            "beta": 1.25,
        })

        # Mock technical indicators
        finance_service.get_technical_indicators = AsyncMock(return_value={
            "sma": {"20": [182, 183, 184, 185], "50": [178, 179, 180, 181]},
            "ema": {"12": [184, 185], "26": [182, 183]},
            "rsi": [60, 62, 65, 63],
            "macd": [{"macd": 1.2, "signal": 0.8, "histogram": 0.4}],
            "bollinger_bands": [{"upper": 190, "middle": 185, "lower": 180}],
            "support_levels": [180, 175, 170],
            "resistance_levels": [190, 195, 200],
        })

        # Mock news sentiment
        finance_service.get_news_sentiment = AsyncMock(return_value={
            "overall_sentiment": {"score": 0.35, "label": "moderately_bullish", "confidence": 0.72},
            "by_symbol": {"AAPL": {"sentiment_score": 0.35, "label": "moderately_bullish", "confidence": 0.72}},
            "key_themes": ["Earnings beat", "AI momentum", "Guidance raise"],
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "executive_summary": "Apple shows strong fundamentals with consistent revenue growth, expanding margins, and robust ecosystem. Technical indicators suggest uptrend continuation. News sentiment moderately bullish.",
                "technical_analysis": {
                    "trend": "uptrend",
                    "trend_strength": 0.75,
                    "key_indicators": {"rsi_14": 63, "macd": {"macd": 1.2, "signal": 0.8}},
                    "support_levels": [180, 175, 170],
                    "resistance_levels": [190, 195, 200],
                    "key_crossovers": ["SMA 20 above SMA 50"],
                },
                "fundamental_analysis": {
                    "valuation": "fair",
                    "financial_health": "strong",
                    "growth_prospects": "moderate",
                    "key_ratios": {"pe_ratio": 28.5, "debt_to_equity": 0.3, "roe": 1.47},
                    "growth_drivers": ["Services growth", "iPhone cycle", "AI integration"],
                    "concerns": ["Valuation premium", "China exposure"],
                },
                "news_sentiment": {
                    "overall_score": 0.35,
                    "label": "moderately_bullish",
                    "confidence": 0.72,
                    "key_themes": ["Earnings beat", "AI momentum", "Guidance raise"],
                },
                "strengths": ["Ecosystem lock-in", "Strong balance sheet", "Consistent innovation"],
                "weaknesses": ["iPhone dependency", "Regulatory risk", "China revenue concentration"],
                "risk_factors": ["Macro slowdown", "Competition", "Supply chain"],
                "growth_drivers": ["Services expansion", "AI integration", "Emerging markets"],
                "investment_outlook": "buy",
                "overall_rating": 8,
                "confidence_score": 0.78,
                "key_recommendations": ["Hold for long-term", "Add on dips below 175", "Monitor China risk"],
            }

            result = await tool.execute({
                "symbol": "AAPL",
                "include_technical": True,
                "include_fundamental": True,
                "include_news": True,
                "llm_provider": "cerebras",
            })

        assert result["symbol"] == "AAPL"
        assert result["company_name"] == "Apple Inc."
        assert result["current_price"] == 185.50
        assert result["currency"] == "USD"
        assert result["llm_provider"] == "cerebras"
        assert result["executive_summary"] is not None
        assert len(result["executive_summary"]) > 50
        assert result["technical_analysis"]["trend"] == "uptrend"
        assert result["fundamental_analysis"]["valuation"] == "fair"
        assert result["news_sentiment"]["overall_score"] == 0.35
        assert result["investment_outlook"] == "buy"
        assert result["overall_rating"] == 8
        assert result["confidence_score"] == 0.78
        assert len(result["strengths"]) >= 3
        assert len(result["weaknesses"]) >= 2
        assert len(result["risk_factors"]) >= 2
        assert len(result["growth_drivers"]) >= 2
        assert len(result["key_recommendations"]) >= 2

    @pytest.mark.asyncio
    async def test_execute_without_technical(self, tool, finance_service):
        """Test analysis without technical indicators."""
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL", "current_price": 185.50, "currency": "USD",
        })
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL", "company_name": "Apple Inc.", "market_cap": 3000000000000,
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "executive_summary": "Summary",
                "technical_analysis": {},
                "fundamental_analysis": {"valuation": "fair", "financial_health": "strong", "growth_prospects": "moderate", "key_ratios": {}, "growth_drivers": [], "concerns": []},
                "news_sentiment": {"overall_score": 0, "label": "neutral", "confidence": 0.5, "key_themes": []},
                "strengths": [], "weaknesses": [], "risk_factors": [], "growth_drivers": [],
                "investment_outlook": "hold", "overall_rating": 5, "confidence_score": 0.5, "key_recommendations": [],
            }

            result = await tool.execute({
                "symbol": "AAPL",
                "include_technical": False,
                "include_fundamental": True,
                "include_news": False,
            })

        # Technical analysis should be empty or minimal
        assert result["technical_analysis"] == {}

    @pytest.mark.asyncio
    async def test_execute_without_fundamental(self, tool, finance_service):
        """Test analysis without fundamental data."""
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL", "current_price": 185.50, "currency": "USD",
        })
        finance_service.get_technical_indicators = AsyncMock(return_value={
            "trend": "uptrend", "support_levels": [180], "resistance_levels": [190],
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "executive_summary": "Summary",
                "technical_analysis": {"trend": "uptrend", "trend_strength": 0.7, "key_indicators": {}, "support_levels": [180], "resistance_levels": [190], "key_crossovers": []},
                "fundamental_analysis": {},
                "news_sentiment": {"overall_score": 0, "label": "neutral", "confidence": 0.5, "key_themes": []},
                "strengths": [], "weaknesses": [], "risk_factors": [], "growth_drivers": [],
                "investment_outlook": "hold", "overall_rating": 5, "confidence_score": 0.5, "key_recommendations": [],
            }

            result = await tool.execute({
                "symbol": "AAPL",
                "include_technical": True,
                "include_fundamental": False,
                "include_news": False,
            })

        assert result["fundamental_analysis"] == {}

    @pytest.mark.asyncio
    async def test_execute_without_news(self, tool, finance_service):
        """Test analysis without news sentiment."""
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL", "current_price": 185.50, "currency": "USD",
        })
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL", "company_name": "Apple Inc.", "market_cap": 3000000000000,
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "executive_summary": "Summary",
                "technical_analysis": {"trend": "uptrend", "trend_strength": 0.7, "key_indicators": {}, "support_levels": [], "resistance_levels": [], "key_crossovers": []},
                "fundamental_analysis": {"valuation": "fair", "financial_health": "strong", "growth_prospects": "moderate", "key_ratios": {}, "growth_drivers": [], "concerns": []},
                "news_sentiment": {},
                "strengths": [], "weaknesses": [], "risk_factors": [], "growth_drivers": [],
                "investment_outlook": "hold", "overall_rating": 5, "confidence_score": 0.5, "key_recommendations": [],
            }

            result = await tool.execute({
                "symbol": "AAPL",
                "include_technical": True,
                "include_fundamental": True,
                "include_news": False,
            })

        assert result["news_sentiment"] == {}

    @pytest.mark.asyncio
    async def test_execute_invalid_symbol(self, tool, finance_service):
        """Test execution with invalid symbol."""
        finance_service.get_stock_quote = AsyncMock(side_effect=FinanceServiceError("Symbol not found"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"symbol": "INVALID"})

    @pytest.mark.asyncio
    async def test_execute_service_error(self, tool, finance_service):
        """Test execution with service error."""
        finance_service.get_stock_quote = AsyncMock(side_effect=FinanceServiceError("Service unavailable"))

        with pytest.raises(FinanceServiceError):
            await tool.execute({"symbol": "AAPL"})

    @pytest.mark.asyncio
    async def test_execute_llm_provider_failover(self, tool, finance_service):
        """Test LLM provider failover."""
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL", "current_price": 185.50, "currency": "USD",
        })
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL", "company_name": "Apple Inc.", "market_cap": 3000000000000,
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [
                Exception("Cerebras unavailable"),
                {
                    "executive_summary": "Fallback analysis",
                    "technical_analysis": {"trend": "uptrend", "trend_strength": 0.5, "key_indicators": {}, "support_levels": [], "resistance_levels": [], "key_crossovers": []},
                    "fundamental_analysis": {"valuation": "fair", "financial_health": "strong", "growth_prospects": "moderate", "key_ratios": {}, "growth_drivers": [], "concerns": []},
                    "news_sentiment": {"overall_score": 0, "label": "neutral", "confidence": 0.5, "key_themes": []},
                    "strengths": [], "weaknesses": [], "risk_factors": [], "growth_drivers": [],
                    "investment_outlook": "hold", "overall_rating": 5, "confidence_score": 0.5, "key_recommendations": [],
                },
            ]

            result = await tool.execute({
                "symbol": "AAPL",
                "llm_provider": "cerebras",
            })

        assert "executive_summary" in result

    @pytest.mark.asyncio
    async def test_execute_confidence_score_range(self, tool, finance_service):
        """Test confidence score is in valid range."""
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL", "current_price": 185.50, "currency": "USD",
        })
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL", "company_name": "Apple Inc.", "market_cap": 3000000000000,
        })

        with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "executive_summary": "Summary",
                "technical_analysis": {"trend": "uptrend", "trend_strength": 0.7, "key_indicators": {}, "support_levels": [], "resistance_levels": [], "key_crossovers": []},
                "fundamental_analysis": {"valuation": "fair", "financial_health": "strong", "growth_prospects": "moderate", "key_ratios": {}, "growth_drivers": [], "concerns": []},
                "news_sentiment": {"overall_score": 0, "label": "neutral", "confidence": 0.5, "key_themes": []},
                "strengths": [], "weaknesses": [], "risk_factors": [], "growth_drivers": [],
                "investment_outlook": "hold", "overall_rating": 5, "confidence_score": 0.85, "key_recommendations": [],
            }

            result = await tool.execute({"symbol": "AAPL"})

        assert 0 <= result["confidence_score"] <= 1
        assert 1 <= result["overall_rating"] <= 10

    @pytest.mark.asyncio
    async def test_execute_investment_outlook_values(self, tool, finance_service):
        """Test investment outlook is valid enum."""
        finance_service.get_stock_quote = AsyncMock(return_value={
            "symbol": "AAPL", "current_price": 185.50, "currency": "USD",
        })
        finance_service.get_company_info = AsyncMock(return_value={
            "symbol": "AAPL", "company_name": "Apple Inc.", "market_cap": 3000000000000,
        })

        valid_outlooks = ["strong_buy", "buy", "hold", "sell", "strong_sell"]

        for outlook in valid_outlooks:
            with patch.object(tool, '_analyze_with_llm', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = {
                    "executive_summary": "Summary",
                    "technical_analysis": {"trend": "uptrend", "trend_strength": 0.7, "key_indicators": {}, "support_levels": [], "resistance_levels": [], "key_crossovers": []},
                    "fundamental_analysis": {"valuation": "fair", "financial_health": "strong", "growth_prospects": "moderate", "key_ratios": {}, "growth_drivers": [], "concerns": []},
                    "news_sentiment": {"overall_score": 0, "label": "neutral", "confidence": 0.5, "key_themes": []},
                    "strengths": [], "weaknesses": [], "risk_factors": [], "growth_drivers": [],
                    "investment_outlook": outlook, "overall_rating": 5, "confidence_score": 0.5, "key_recommendations": [],
                }

                result = await tool.execute({"symbol": "AAPL"})
                # The tool returns placeholder "buy" for the investment_outlook
                # The mock is only used when _analyze_with_llm is called
                # Since we're mocking it, we should see the mocked value
                assert result["investment_outlook"] == outlook

    def test_tool_metadata(self, tool):
        """Test tool metadata."""
        assert tool.name == "financial_analysis"
        assert "analysis" in tool.description.lower()
        assert "llm" in tool.description.lower()
        assert "finance" in tool.tags
        assert tool.version == "1.0.0"
        assert tool.author == "ToolBridge"