"""JSON Schemas for Advanced Finance Tools.

Defines input/output schemas for all advanced financial tools.
"""

from typing import Any

# Historical Price Tool Schemas
HISTORICAL_PRICE_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock symbol (e.g., AAPL, RELIANCE.NS, BMW.DE)",
            "pattern": "^[A-Z0-9.\\-]{1,10}$",
            "minLength": 1,
            "maxLength": 10,
        },
        "period": {
            "type": "string",
            "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
            "description": "Time period for historical data",
            "default": "1mo",
        },
        "interval": {
            "type": "string",
            "enum": ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"],
            "description": "Data interval",
            "default": "1d",
        },
        "start_date": {
            "type": "string",
            "description": "Start date (YYYY-MM-DD)",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        },
        "end_date": {
            "type": "string",
            "description": "End date (YYYY-MM-DD)",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        },
        "include_adjusted_close": {
            "type": "boolean",
            "description": "Include adjusted close prices",
            "default": True,
        },
        "include_dividends": {
            "type": "boolean",
            "description": "Include dividend data",
            "default": False,
        },
        "include_splits": {
            "type": "boolean",
            "description": "Include stock split data",
            "default": False,
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

HISTORICAL_PRICE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "name": {"type": "string"},
        "currency": {"type": "string"},
        "exchange": {"type": "string"},
        "period": {"type": "string"},
        "interval": {"type": "string"},
        "data_points": {"type": "integer"},
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "format": "date-time"},
                    "open": {"type": "number"},
                    "high": {"type": "number"},
                    "low": {"type": "number"},
                    "close": {"type": "number"},
                    "adjusted_close": {"type": "number"},
                    "volume": {"type": "integer"},
                    "dividends": {"type": "number"},
                    "stock_splits": {"type": "number"},
                },
                "required": ["date", "open", "high", "low", "close", "volume"],
            },
        },
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["symbol", "data", "source", "timestamp"],
    "additionalProperties": False,
}

# Company Information Tool Schemas
COMPANY_INFO_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock symbol (e.g., AAPL, RELIANCE.NS, BMW.DE)",
            "pattern": "^[A-Z0-9.\\-]{1,10}$",
            "minLength": 1,
            "maxLength": 10,
        },
        "include_financials": {
            "type": "boolean",
            "description": "Include key financial metrics",
            "default": True,
        },
        "include_leadership": {
            "type": "boolean",
            "description": "Include leadership/management info",
            "default": True,
        },
        "include_statistics": {
            "type": "boolean",
            "description": "Include key statistics",
            "default": True,
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

COMPANY_INFO_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "name": {"type": "string"},
        "currency": {"type": "string"},
        "exchange": {"type": "string"},
        "sector": {"type": "string"},
        "industry": {"type": "string"},
        "description": {"type": "string"},
        "website": {"type": "string"},
        "ceo": {"type": "string"},
        "employees": {"type": "integer"},
        "headquarters": {"type": "string"},
        "market_cap": {"type": "integer"},
        "enterprise_value": {"type": "integer"},
        "shares_outstanding": {"type": "integer"},
        "float_shares": {"type": "integer"},
        "pe_ratio": {"type": "number"},
        "forward_pe": {"type": "number"},
        "peg_ratio": {"type": "number"},
        "price_to_book": {"type": "number"},
        "price_to_sales": {"type": "number"},
        "dividend_yield": {"type": "number"},
        "dividend_rate": {"type": "number"},
        "payout_ratio": {"type": "number"},
        "beta": {"type": "number"},
        "eps": {"type": "number"},
        "revenue": {"type": "integer"},
        "gross_profit": {"type": "integer"},
        "ebitda": {"type": "integer"},
        "net_income": {"type": "integer"},
        "profit_margin": {"type": "number"},
        "operating_margin": {"type": "number"},
        "return_on_equity": {"type": "number"},
        "return_on_assets": {"type": "number"},
        "debt_to_equity": {"type": "number"},
        "current_ratio": {"type": "number"},
        "quick_ratio": {"type": "number"},
        "fifty_two_week_high": {"type": "number"},
        "fifty_two_week_low": {"type": "number"},
        "fifty_day_average": {"type": "number"},
        "two_hundred_day_average": {"type": "number"},
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["symbol", "name", "currency", "exchange", "source", "timestamp"],
    "additionalProperties": False,
}

# Market Movers Tool Schemas
MARKET_MOVERS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["gainers", "losers", "most_active", "trending", "summary"],
            "description": "Type of market movers to fetch",
            "default": "gainers",
        },
        "market": {
            "type": "string",
            "enum": ["US", "IN", "EU", "ALL"],
            "description": "Market to query",
            "default": "US",
        },
        "limit": {
            "type": "integer",
            "description": "Number of results to return",
            "minimum": 1,
            "maximum": 50,
            "default": 10,
        },
    },
    "required": ["type"],
    "additionalProperties": False,
}

MARKET_MOVERS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string"},
        "market": {"type": "string"},
        "count": {"type": "integer"},
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                    "change": {"type": "number"},
                    "change_percent": {"type": "number"},
                    "volume": {"type": "integer"},
                    "market_cap": {"type": "integer"},
                },
                "required": ["symbol", "name", "price", "change", "change_percent", "volume"],
            },
        },
        "market_summary": {
            "type": "object",
            "properties": {
                "market": {"type": "string"},
                "total_stocks": {"type": "integer"},
                "advancing": {"type": "integer"},
                "declining": {"type": "integer"},
                "unchanged": {"type": "integer"},
            },
        },
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["type", "market", "count", "data", "source", "timestamp"],
    "additionalProperties": False,
}

# Technical Indicators Tool Schemas
TECHNICAL_INDICATORS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock symbol (e.g., AAPL, RELIANCE.NS)",
            "pattern": "^[A-Z0-9.\\-]{1,10}$",
            "minLength": 1,
            "maxLength": 10,
        },
        "indicators": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "sma", "ema", "rsi", "macd", "bollinger_bands",
                    "atr", "vwap", "sma_crossover", "support_resistance", "trend"
                ],
            },
            "description": "List of indicators to calculate",
            "minItems": 1,
        },
        "period": {
            "type": "string",
            "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
            "description": "Time period for historical data",
            "default": "3mo",
        },
        "interval": {
            "type": "string",
            "enum": ["1d", "5d", "1wk", "1mo"],
            "description": "Data interval",
            "default": "1d",
        },
        "sma_periods": {
            "type": "array",
            "items": {"type": "integer", "minimum": 2, "maximum": 200},
            "description": "SMA periods to calculate",
            "default": [20, 50, 200],
        },
        "ema_periods": {
            "type": "array",
            "items": {"type": "integer", "minimum": 2, "maximum": 200},
            "description": "EMA periods to calculate",
            "default": [12, 26],
        },
        "rsi_period": {
            "type": "integer",
            "minimum": 2,
            "maximum": 50,
            "default": 14,
            "description": "RSI period",
        },
        "macd_fast": {
            "type": "integer",
            "minimum": 2,
            "maximum": 50,
            "default": 12,
            "description": "MACD fast period",
        },
        "macd_slow": {
            "type": "integer",
            "minimum": 2,
            "maximum": 100,
            "default": 26,
            "description": "MACD slow period",
        },
        "macd_signal": {
            "type": "integer",
            "minimum": 2,
            "maximum": 50,
            "default": 9,
            "description": "MACD signal period",
        },
        "bb_period": {
            "type": "integer",
            "minimum": 5,
            "maximum": 100,
            "default": 20,
            "description": "Bollinger Bands period",
        },
        "bb_std": {
            "type": "number",
            "minimum": 0.5,
            "maximum": 5,
            "default": 2,
            "description": "Bollinger Bands standard deviation multiplier",
        },
    },
    "required": ["symbol", "indicators"],
    "additionalProperties": False,
}

TECHNICAL_INDICATORS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "name": {"type": "string"},
        "period": {"type": "string"},
        "interval": {"type": "string"},
        "indicators": {
            "type": "object",
            "properties": {
                "sma": {
                    "type": "object",
                    "description": "Simple Moving Averages",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "format": "date-time"},
                                "value": {"type": "number"},
                            },
                        },
                    },
                },
                "ema": {
                    "type": "object",
                    "description": "Exponential Moving Averages",
                    "additionalProperties": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "format": "date-time"},
                                "value": {"type": "number"},
                            },
                        },
                    },
                },
                "rsi": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date-time"},
                            "value": {"type": "number"},
                        },
                    },
                    "description": "Relative Strength Index",
                },
                "macd": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date-time"},
                            "macd": {"type": "number"},
                            "signal": {"type": "number"},
                            "histogram": {"type": "number"},
                        },
                    },
                },
                "bollinger_bands": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date-time"},
                            "upper": {"type": "number"},
                            "middle": {"type": "number"},
                            "lower": {"type": "number"},
                            "bandwidth": {"type": "number"},
                            "percent_b": {"type": "number"},
                        },
                    },
                },
                "atr": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date-time"},
                            "value": {"type": "number"},
                        },
                    },
                    "description": "Average True Range",
                },
                "vwap": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date-time"},
                            "value": {"type": "number"},
                        },
                    },
                    "description": "Volume Weighted Average Price",
                },
                "sma_crossovers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date-time"},
                            "fast_period": {"type": "integer"},
                            "slow_period": {"type": "integer"},
                            "crossover_type": {"type": "string", "enum": ["golden_cross", "death_cross"]},
                        },
                    },
                    "description": "Moving Average Crossovers",
                },
                "support_resistance": {
                    "type": "object",
                    "properties": {
                        "support_levels": {
                            "type": "array",
                            "items": {"type": "number"},
                        },
                        "resistance_levels": {
                            "type": "array",
                            "items": {"type": "number"},
                        },
                        "current_price": {"type": "number"},
                        "nearest_support": {"type": "number"},
                        "nearest_resistance": {"type": "number"},
                    },
                },
                "trend": {
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["uptrend", "downtrend", "sideways"]},
                        "strength": {"type": "number", "minimum": 0, "maximum": 1},
                        "duration_days": {"type": "integer"},
                        "key_levels": {"type": "array", "items": {"type": "number"}},
                    },
                },
            },
        },
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["symbol", "indicators", "source", "timestamp"],
    "additionalProperties": False,
}

# Financial News Tool Schemas
FINANCIAL_NEWS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbols": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[A-Z0-9.\\-]{1,10}$"},
            "description": "Stock symbols to filter news (optional)",
            "maxItems": 20,
        },
        "category": {
            "type": "string",
            "enum": ["general", "earnings", "mergers", "ipo", "analyst_rating", "dividend", "split", "guidance", "insider_trading", "sec_filing"],
            "description": "News category filter",
        },
        "country": {
            "type": "string",
            "description": "Country filter (ISO 3166-1 alpha-2)",
            "pattern": "^[A-Z]{2}$",
        },
        "limit": {
            "type": "integer",
            "minimum": 1,
            "maximum": 100,
            "default": 20,
            "description": "Maximum number of articles",
        },
        "start_date": {
            "type": "string",
            "description": "Start date (YYYY-MM-DD)",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        },
        "end_date": {
            "type": "string",
            "description": "End date (YYYY-MM-DD)",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        },
    },
    "additionalProperties": False,
}

FINANCIAL_NEWS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "total_articles": {"type": "integer"},
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "url": {"type": "string"},
                    "source": {"type": "string"},
                    "category": {"type": "string"},
                    "symbols": {"type": "array", "items": {"type": "string"}},
                    "published_at": {"type": "string", "format": "date-time"},
                    "image_url": {"type": "string"},
                },
                "required": ["id", "title", "summary", "url", "source", "published_at"],
            },
        },
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["total_articles", "articles", "source", "timestamp"],
    "additionalProperties": False,
}

# News Sentiment Tool Schemas
NEWS_SENTIMENT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbols": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[A-Z0-9.\\-]{1,10}$"},
            "description": "Stock symbols to analyze (required)",
            "minItems": 1,
            "maxItems": 10,
        },
        "lookback_days": {
            "type": "integer",
            "minimum": 1,
            "maximum": 30,
            "default": 7,
            "description": "Days of news to analyze",
        },
        "llm_provider": {
            "type": "string",
            "enum": ["cerebras", "nvidia", "openrouter"],
            "description": "LLM provider for sentiment analysis",
            "default": "cerebras",
        },
        "model": {
            "type": "string",
            "description": "Specific model to use (optional)",
        },
    },
    "required": ["symbols"],
    "additionalProperties": False,
}

NEWS_SENTIMENT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbols_analyzed": {"type": "array", "items": {"type": "string"}},
        "lookback_days": {"type": "integer"},
        "llm_provider": {"type": "string"},
        "model": {"type": "string"},
        "total_articles_analyzed": {"type": "integer"},
        "overall_sentiment": {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": -1, "maximum": 1},
                "label": {"type": "string", "enum": ["very_bearish", "bearish", "neutral", "bullish", "very_bullish"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "by_symbol": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "properties": {
                    "sentiment_score": {"type": "number", "minimum": -1, "maximum": 1},
                    "label": {"type": "string", "enum": ["very_bearish", "bearish", "neutral", "bullish", "very_bullish"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "articles_count": {"type": "integer"},
                    "key_themes": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                },
            },
        },
        "llm_explanation": {"type": "string"},
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["symbols_analyzed", "overall_sentiment", "by_symbol", "llm_explanation", "source", "timestamp"],
    "additionalProperties": False,
}

# Financial Analysis Tool Schemas
FINANCIAL_ANALYSIS_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock symbol to analyze",
            "pattern": "^[A-Z0-9.\\-]{1,10}$",
            "minLength": 1,
            "maxLength": 10,
        },
        "include_technical": {
            "type": "boolean",
            "default": True,
            "description": "Include technical analysis",
        },
        "include_fundamental": {
            "type": "boolean",
            "default": True,
            "description": "Include fundamental analysis",
        },
        "include_news": {
            "type": "boolean",
            "default": True,
            "description": "Include news sentiment",
        },
        "llm_provider": {
            "type": "string",
            "enum": ["cerebras", "nvidia", "openrouter"],
            "description": "LLM provider for analysis",
            "default": "cerebras",
        },
        "model": {
            "type": "string",
            "description": "Specific model to use (optional)",
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

FINANCIAL_ANALYSIS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string"},
        "company_name": {"type": "string"},
        "current_price": {"type": "number"},
        "currency": {"type": "string"},
        "llm_provider": {"type": "string"},
        "model": {"type": "string"},
        "executive_summary": {"type": "string"},
        "technical_analysis": {
            "type": "object",
            "properties": {
                "trend": {"type": "string", "enum": ["uptrend", "downtrend", "sideways"]},
                "trend_strength": {"type": "number", "minimum": 0, "maximum": 1},
                "key_indicators": {"type": "object"},
                "support_levels": {"type": "array", "items": {"type": "number"}},
                "resistance_levels": {"type": "array", "items": {"type": "number"}},
                "key_crossovers": {"type": "array", "items": {"type": "string"}},
            },
        },
        "fundamental_analysis": {
            "type": "object",
            "properties": {
                "valuation": {"type": "string", "enum": ["undervalued", "fair", "overvalued"]},
                "financial_health": {"type": "string", "enum": ["strong", "moderate", "weak"]},
                "growth_prospects": {"type": "string", "enum": ["high", "moderate", "low"]},
                "key_ratios": {"type": "object"},
                "growth_drivers": {"type": "array", "items": {"type": "string"}},
                "concerns": {"type": "array", "items": {"type": "string"}},
            },
        },
        "news_sentiment": {
            "type": "object",
            "properties": {
                "overall_score": {"type": "number", "minimum": -1, "maximum": 1},
                "label": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "key_themes": {"type": "array", "items": {"type": "string"}},
            },
        },
        "strengths": {"type": "array", "items": {"type": "string"}},
        "weaknesses": {"type": "array", "items": {"type": "string"}},
        "risk_factors": {"type": "array", "items": {"type": "string"}},
        "growth_drivers": {"type": "array", "items": {"type": "string"}},
        "investment_outlook": {
            "type": "string",
            "enum": ["strong_buy", "buy", "hold", "sell", "strong_sell"],
        },
        "overall_rating": {"type": "number", "minimum": 1, "maximum": 10},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "key_recommendations": {"type": "array", "items": {"type": "string"}},
        "source": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
    },
    "required": ["symbol", "executive_summary", "investment_outlook", "overall_rating", "confidence_score", "source", "timestamp"],
    "additionalProperties": False,
}