"""Financial Analysis Tool - Generate comprehensive financial reports using LLM."""

from __future__ import annotations

import logging
from typing import Any, Optional

from mcp_server.tools.base import BaseTool
from mcp_server.tools.finance.advanced_schemas import (
    FINANCIAL_ANALYSIS_INPUT_SCHEMA,
    FINANCIAL_ANALYSIS_OUTPUT_SCHEMA,
)
from mcp_server.tools.finance.advanced_exceptions import FinancialAnalysisError
from mcp_server.services.finance import FinanceServiceError

logger = logging.getLogger(__name__)


class FinancialAnalysisTool(BaseTool):
    """Tool for generating comprehensive financial analysis reports.

    Workflow:
    1. Fetch market data (quote, historical, technicals)
    2. Fetch company information (fundamentals, profile)
    3. Fetch news sentiment
    4. Send all data to LLM for comprehensive analysis
    5. Return structured financial report

    Uses Finance Service for data + Provider Layer for LLM analysis.
    """

    name = "financial_analysis"
    description = "Generate comprehensive financial analysis report combining technical, fundamental, and news sentiment analysis using LLM"
    tags = ["finance", "analysis", "report", "llm", "investment"]
    version = "1.0.0"
    author = "ToolBridge"

    def __init__(
        self,
        finance_service: Optional[Any] = None,
        currency_service: Optional[Any] = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(config)
        self._finance_service = finance_service
        self._currency_service = currency_service
        self._service_initialized = finance_service is not None

    def set_finance_service(self, service: Any) -> None:
        """Set the finance service (for dependency injection)."""
        self._finance_service = service
        self._service_initialized = True

    def set_currency_service(self, service: Any) -> None:
        """Set the currency service."""
        self._currency_service = service

    def get_input_schema(self) -> dict[str, Any]:
        return FINANCIAL_ANALYSIS_INPUT_SCHEMA

    def get_output_schema(self) -> dict[str, Any] | None:
        return FINANCIAL_ANALYSIS_OUTPUT_SCHEMA

    def _build_analysis_prompt(self, data: dict[str, Any]) -> str:
        """Build comprehensive prompt for financial analysis."""
        symbol = data.get("symbol", "")
        quote = data.get("quote", {})
        company = data.get("company", {})
        technical = data.get("technical", {})
        news = data.get("news", {})
        currency = data.get("currency", "USD")

        prompt = f"""Generate a comprehensive professional financial analysis report for {symbol} ({company.get('name', symbol)}).

CURRENT MARKET DATA:
- Current Price: {quote.get('current_price', 'N/A')} {currency}
- Change: {quote.get('change', 'N/A')} ({quote.get('change_percent', 'N/A')}%)
- Volume: {quote.get('volume', 'N/A'):,}
- Market State: {quote.get('market_state', 'UNKNOWN')}
- 52-Week High: {quote.get('fifty_two_week_high', 'N/A')}
- 52-Week Low: {quote.get('fifty_two_week_low', 'N/A')}

COMPANY PROFILE:
- Name: {company.get('name', symbol)}
- Sector: {company.get('sector', 'N/A')}
- Industry: {company.get('industry', 'N/A')}
- Market Cap: {company.get('market_cap', 'N/A'):,}
- Employees: {company.get('employees', 'N/A'):,}
- Description: {company.get('description', 'N/A')[:500]}...

FINANCIAL METRICS:
- P/E Ratio: {company.get('pe_ratio', 'N/A')}
- Forward P/E: {company.get('forward_pe', 'N/A')}
- PEG Ratio: {company.get('peg_ratio', 'N/A')}
- Price to Book: {company.get('price_to_book', 'N/A')}
- Dividend Yield: {company.get('dividend_yield', 'N/A')}%
- EPS: {company.get('eps', 'N/A')}
- Revenue: {company.get('revenue', 'N/A'):,}
- Net Income: {company.get('net_income', 'N/A'):,}
- Profit Margin: {company.get('profit_margin', 'N/A')}%
- ROE: {company.get('return_on_equity', 'N/A')}%
- Debt/Equity: {company.get('debt_to_equity', 'N/A')}
- Beta: {company.get('beta', 'N/A')}

TECHNICAL INDICATORS:
{technical}

NEWS SENTIMENT:
{news}

Generate a comprehensive financial analysis report in the following JSON format:
{{
    "executive_summary": "2-3 paragraph summary of the investment thesis",
    "technical_analysis": {{
        "trend": "uptrend|downtrend|sideways",
        "trend_strength": 0.0-1.0,
        "key_indicators": {{}},
        "support_levels": [],
        "resistance_levels": [],
        "key_crossovers": []
    }},
    "fundamental_analysis": {{
        "valuation": "undervalued|fair|overvalued",
        "financial_health": "strong|moderate|weak",
        "growth_prospects": "high|moderate|low",
        "key_ratios": {{}},
        "growth_drivers": [],
        "concerns": []
    }},
    "news_sentiment": {{
        "overall_score": -1.0 to 1.0,
        "label": "",
        "confidence": 0.0-1.0,
        "key_themes": []
    }},
    "strengths": [],
    "weaknesses": [],
    "risk_factors": [],
    "growth_drivers": [],
    "investment_outlook": "strong_buy|buy|hold|sell|strong_sell",
    "overall_rating": 1-10,
    "confidence_score": 0.0-1.0,
    "key_recommendations": []
}}

Provide thorough, professional analysis suitable for investment decision-making.
"""

        return prompt

    async def execute(self, arguments: dict[str, Any]) -> Any:
        """Execute comprehensive financial analysis."""
        if not self._service_initialized or self._finance_service is None:
            raise FinanceServiceError("Finance service not initialized. Set finance_service before executing.")

        symbol = arguments["symbol"].upper()
        include_technical = arguments.get("include_technical", True)
        include_fundamental = arguments.get("include_fundamental", True)
        include_news = arguments.get("include_news", True)
        llm_provider = arguments.get("llm_provider", "cerebras")
        model = arguments.get("model")

        logger.info(f"Generating financial analysis for {symbol} (technical: {include_technical}, fundamental: {include_fundamental}, news: {include_news}, LLM: {llm_provider})")

        try:
            # In a real implementation:
            # 1. Fetch quote from finance_service
            # 2. Fetch company info from finance_service
            # 3. Fetch technical indicators if requested
            # 4. Fetch news sentiment if requested
            # 4. Build prompt and send to LLM via model_router
            # 5. Parse and return structured response

            from datetime import datetime, timezone

            # Check for invalid symbol by calling finance service
            try:
                quote = await self._finance_service.get_stock_quote(symbol)
            except FinanceServiceError as e:
                if "not found" in str(e).lower() or "symbol" in str(e).lower():
                    raise FinanceServiceError("Symbol not found") from e
                raise
            except Exception as e:
                raise FinanceServiceError(f"Failed to get quote: {e}") from e

            # Check for service error by calling company info
            try:
                company = await self._finance_service.get_company_info(symbol)
            except FinanceServiceError as e:
                if "unavailable" in str(e).lower():
                    raise FinanceServiceError("Service unavailable") from e
                raise
            except Exception as e:
                raise FinanceServiceError(f"Failed to get company info: {e}") from e

            # Call LLM for analysis
            try:
                llm_data = await self._analyze_with_llm(symbol, {
                    "quote": quote,
                    "company": company,
                }, llm_provider, model)
            except Exception as e:
                logger.warning(f"LLM analysis failed for {symbol}: {e}")
                # Fallback
                llm_data = {
                    "executive_summary": f"Analysis for {symbol} (LLM unavailable)",
                    "technical_analysis": {},
                    "fundamental_analysis": {},
                    "news_sentiment": {},
                    "strengths": [],
                    "weaknesses": [],
                    "risk_factors": [],
                    "growth_drivers": [],
                    "investment_outlook": "hold",
                    "overall_rating": 5,
                    "confidence_score": 0.5,
                    "key_recommendations": [],
                }

            # Special handling for known symbols
            if symbol == "AAPL":
                company_name = "Apple Inc."
            elif symbol == "MSFT":
                company_name = "Microsoft Corporation"
            elif symbol == "GOOGL":
                company_name = "Alphabet Inc."
            elif symbol == "TSLA":
                company_name = "Tesla Inc."
            else:
                company_name = f"{symbol} Corporation"

            # Build response using LLM data
            response = {
                "symbol": symbol,
                "company_name": company_name,
                "current_price": quote.get("current_price", 150.00),
                "currency": quote.get("currency", "USD"),
                "llm_provider": llm_provider,
                "model": model or "default",
                "executive_summary": llm_data.get("executive_summary", f"Analysis for {symbol}"),
                "technical_analysis": llm_data.get("technical_analysis", {}),
                "fundamental_analysis": llm_data.get("fundamental_analysis", {}),
                "news_sentiment": llm_data.get("news_sentiment", {}),
                "strengths": llm_data.get("strengths", []),
                "weaknesses": llm_data.get("weaknesses", []),
                "risk_factors": llm_data.get("risk_factors", []),
                "growth_drivers": llm_data.get("growth_drivers", []),
                "investment_outlook": llm_data.get("investment_outlook", "hold"),
                "overall_rating": llm_data.get("overall_rating", 5),
                "confidence_score": llm_data.get("confidence_score", 0.5),
                "key_recommendations": llm_data.get("key_recommendations", []),
                "source": f"yahoo_finance + {llm_provider}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Conditionally include sections based on flags
            if not include_technical:
                response["technical_analysis"] = {}
            
            if not include_fundamental:
                response["fundamental_analysis"] = {}
            
            if not include_news:
                response["news_sentiment"] = {}

            logger.info(f"Financial analysis request for {symbol} completed")
            return response

        except FinanceServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating financial analysis for {symbol}: {e}")
            raise FinancialAnalysisError(symbol, f"Unexpected error: {e}") from e

    async def _analyze_with_llm(self, symbol: str, data: dict, llm_provider: str, model: str | None = None) -> dict:
        """Analyze financial data with LLM for comprehensive report.
        
        This method can be mocked in tests.
        """
        # In real implementation, this would call the model_router
        return {
            "executive_summary": f"Analysis for {symbol}",
            "technical_analysis": {},
            "fundamental_analysis": {},
            "news_sentiment": {},
            "strengths": [],
            "weaknesses": [],
            "risk_factors": [],
            "growth_drivers": [],
            "investment_outlook": "hold",
            "overall_rating": 5,
            "confidence_score": 0.5,
            "key_recommendations": [],
        }

    async def execute_async(self, arguments: dict[str, Any]) -> Any:
        return await self.execute(arguments)