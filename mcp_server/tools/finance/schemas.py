"""JSON Schemas for Finance Tools.

Defines input/output schemas for stock price and currency exchange tools.
"""

from typing import Any

# Stock Price Tool Schemas
STOCK_PRICE_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock symbol (e.g., AAPL, MSFT, RELIANCE.NS, BMW.DE)",
            "pattern": "^[A-Z0-9.\\-]{1,10}$",
            "minLength": 1,
            "maxLength": 10,
        },
        "market": {
            "type": "string",
            "enum": ["US", "IN", "UK", "DE", "FR", "JP", "HK", "SG", "AUTO"],
            "description": "Market/exchange (auto-detected if not specified)",
            "default": "AUTO",
        },
        "include_company_info": {
            "type": "boolean",
            "description": "Include company details (sector, industry, market cap, etc.)",
            "default": True,
        },
        "include_history": {
            "type": "boolean",
            "description": "Include recent price history",
            "default": False,
        },
        "history_period": {
            "type": "string",
            "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
            "description": "Period for price history",
            "default": "1mo",
        },
    },
    "required": ["symbol"],
    "additionalProperties": False,
}

STOCK_PRICE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "symbol": {
            "type": "string",
            "description": "Stock symbol",
        },
        "name": {
            "type": "string",
            "description": "Company name",
        },
        "currency": {
            "type": "string",
            "description": "Trading currency (USD, INR, EUR, etc.)",
        },
        "exchange": {
            "type": "string",
            "description": "Exchange name (NASDAQ, NYSE, NSE, BSE, XETRA, etc.)",
        },
        "current_price": {
            "type": "number",
            "description": "Current/latest price",
        },
        "open": {
            "type": "number",
            "description": "Day's open price",
        },
        "high": {
            "type": "number",
            "description": "Day's high price",
        },
        "low": {
            "type": "number",
            "description": "Day's low price",
        },
        "previous_close": {
            "type": "number",
            "description": "Previous day's close price",
        },
        "volume": {
            "type": "integer",
            "description": "Trading volume",
        },
        "change": {
            "type": "number",
            "description": "Price change from previous close",
        },
        "change_percent": {
            "type": "number",
            "description": "Percentage change from previous close",
        },
        "market_cap": {
            "type": "integer",
            "description": "Market capitalization (if available)",
        },
        "sector": {
            "type": "string",
            "description": "Business sector",
        },
        "industry": {
            "type": "string",
            "description": "Industry classification",
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Data timestamp (ISO 8601)",
        },
        "market_state": {
            "type": "string",
            "enum": ["OPEN", "CLOSED", "PRE_MARKET", "POST_MARKET", "UNKNOWN"],
            "description": "Current market state",
        },
        "fifty_two_week_high": {
            "type": "number",
            "description": "52-week high",
        },
        "fifty_two_week_low": {
            "type": "number",
            "description": "52-week low",
        },
        "avg_volume": {
            "type": "integer",
            "description": "Average daily volume",
        },
        "pe_ratio": {
            "type": "number",
            "description": "Price-to-earnings ratio (if available)",
        },
        "dividend_yield": {
            "type": "number",
            "description": "Dividend yield (if available)",
        },
        "source": {
            "type": "string",
            "description": "Data provider source",
        },
    },
    "required": [
        "symbol", "name", "currency", "exchange", "current_price",
        "open", "high", "low", "previous_close", "volume",
        "change", "change_percent", "timestamp", "market_state", "source",
    ],
    "additionalProperties": False,
}

# Currency Exchange Tool Schemas
CURRENCY_EXCHANGE_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "from_currency": {
            "type": "string",
            "description": "Source currency code (ISO 4217, e.g., USD, EUR, INR)",
            "pattern": "^[A-Z]{3}$",
            "minLength": 3,
            "maxLength": 3,
        },
        "to_currency": {
            "type": "string",
            "description": "Target currency code (ISO 4217)",
            "pattern": "^[A-Z]{3}$",
            "minLength": 3,
            "maxLength": 3,
        },
        "amount": {
            "type": "number",
            "description": "Amount to convert",
            "minimum": 0.000001,
            "default": 1.0,
        },
        "date": {
            "type": "string",
            "description": "Historical rate date (YYYY-MM-DD) or 'latest'",
            "pattern": "^(\\d{4}-\\d{2}-\\d{2}|latest)$",
        },
        "include_supported": {
            "type": "boolean",
            "description": "Include list of all supported currencies in response",
            "default": False,
        },
    },
    "required": ["from_currency", "to_currency"],
    "additionalProperties": False,
}

CURRENCY_EXCHANGE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "from_currency": {
            "type": "string",
            "description": "Source currency code",
        },
        "to_currency": {
            "type": "string",
            "description": "Target currency code",
        },
        "rate": {
            "type": "number",
            "description": "Exchange rate (1 from_currency = rate to_currency)",
        },
        "amount": {
            "type": "number",
            "description": "Original amount",
        },
        "converted_amount": {
            "type": "number",
            "description": "Converted amount in target currency",
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Rate timestamp",
        },
        "date": {
            "type": "string",
            "description": "Rate date (YYYY-MM-DD)",
        },
        "source": {
            "type": "string",
            "description": "Data provider source",
        },
        "supported_currencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of all supported currency codes (if requested)",
        },
    },
    "required": [
        "from_currency", "to_currency", "rate", "amount",
        "converted_amount", "timestamp", "date", "source",
    ],
    "additionalProperties": False,
}

# Supported Currencies Tool Schemas
SUPPORTED_CURRENCIES_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}

SUPPORTED_CURRENCIES_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "currencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "name": {"type": "string"},
                    "symbol": {"type": "string"},
                },
                "required": ["code", "name", "symbol"],
            },
        },
        "count": {"type": "integer"},
    },
    "required": ["currencies", "count"],
    "additionalProperties": False,
}