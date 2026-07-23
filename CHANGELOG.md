# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-07-23

### Added - Phase 1: Project Foundation
- Clean architecture skeleton with domain-driven design
- Configuration management via Pydantic v2 Settings with environment variable support
- Structured logging with Python standard library
- Base exception hierarchy with MCP-specific errors
- Base models with Pydantic v2 validation
- Provider abstraction interface
- Utility helpers

### Added - Phase 2: MCP Core Engine
- **Tool System:** BaseTool, ToolMetadata, ToolRegistry, ToolManager with dependency injection
- **Validation:** JSON Schema validation, Request/Response validation for MCP protocol
- **MCP Protocol:** FastMCP server with tools/list, tools/call, initialize, ping handlers
- **Health & Version:** Liveness, readiness, full health endpoints with service registration
- **Core Server:** FastMCP server with proper initialization and handler registration

### Added - Phase 3: Provider Abstraction Layer
- **Provider Interface:** ProviderBase with health checks, metrics, retry logic, token usage tracking
- **LLM Providers:**
  - Cerebras (llama3.1-8b, 70b, 405b)
  - NVIDIA NIM
  - OpenRouter
- **Provider Factory:** Dynamic provider registration, instantiation, and lifecycle management
- **Model Router:** 6 routing strategies (AUTO, FAST, SMART, COST_OPTIMAL, SPECIFIC, FALLBACK_CHAIN)
- **Automatic Failover:** Circuit breaker pattern, health monitoring, retry with exponential backoff

### Added - Sprint 4.1: Enterprise Financial Services Layer
- **FinanceService:** High-level stock market data service with provider failover
- **CurrencyService:** High-level currency exchange service with conversion
- **Provider Router:** Automatic failover with health monitoring and metrics
- **Health Monitor:** Background health checks with configurable intervals and alerts
- **Metrics Collector:** Service/provider metrics (latency, success/fail rates, cache hits/misses)
- **Finance Cache:** TTL-based caching (stock: 30s, currency: 5min, currencies: 24h) with LRU eviction
- **Stock Providers (5):** Yahoo Finance, Alpha Vantage, Twelve Data, Finnhub, Polygon
- **Currency Providers (3):** Frankfurter (ECB), ExchangeRate-API, CurrencyLayer
- **MCP Tools:** `stock_price`, `currency_exchange`, `supported_currencies`

### Added - Sprint 4.2: Advanced Financial Intelligence Tools
- **Historical Price Tool:** OHLCV data, multiple intervals (1m-1mo), date ranges, adjusted close, dividends, splits
- **Company Info Tool:** Profile, financials, leadership, key statistics, dividends, splits, 52-week high/low
- **Market Movers Tool:** Top gainers, losers, most active, trending, market summary, sector performance
- **Technical Indicators Tool (10 indicators):** SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, SMA Crossovers, Support/Resistance, Trend Detection
- **Financial News Tool:** Company/market/sector news with category/country/date filters, breaking news
- **News Sentiment Tool:** LLM-powered sentiment analysis (bullish/bearish/neutral), confidence scores, key themes
- **Financial Analysis Tool:** Comprehensive LLM-generated investment reports with executive summary, technical/fundamental analysis, news sentiment, strengths/weaknesses, risk factors, investment outlook, rating (1-10)

### Added - Infrastructure & Configuration
- **pyproject.toml:** Complete build configuration with Ruff, Black, MyPy, Bandit, pytest
- **requirements.txt:** Runtime dependencies (pydantic, pydantic-settings, uvicorn, mcp, jsonschema, numpy, aiohttp)
- **LICENSE:** MIT License
- **README.md:** Comprehensive documentation with badges, architecture diagram, quick start
- **RELEASE_NOTES.md:** Detailed release notes for v1.0.0
- **FINAL_RELEASE_REPORT.md:** Complete verification audit report

### Added - Testing
- **Total Tests:** 344 (100% passing)
- **Phase 1-3 Tests:** ~254 tests
- **Sprint 4.1 Tests:** 17 tests (FinanceCache)
- **Sprint 4.2 Tests:** 73 tests (7 new financial tools)
- **Test Coverage Config:** Available in pyproject.toml

### Changed
- **Settings:** Extended with provider API keys, routing configuration, cache/timeout/retry settings
- **Provider Base:** Enhanced with metrics, health checks, token usage, cost estimation
- **Tool System:** Updated with dependency injection pattern for services
- **Requirements:** Added numpy>=1.24.0, aiohttp>=3.8.0 for technical indicators and HTTP clients

### Fixed
- FinanceCache TTL expiration edge case (negative TTL handling)
- LRU eviction with access counter tracking
- TechnicalIndicatorsTool calculator delegation pattern
- FinancialAnalysisTool LLM provider failover with graceful degradation
- FinancialNewsTool limit enforcement preserving total_articles count
- NewsSentimentTool per-symbol LLM exception handling with neutral fallback
- COMPANY_INFO_INPUT_SCHEMA field naming (include_leadership, include_statistics)
- ATR calculation array bounds for period+1 requirement
- Investment outlook enum values consistency across tools

### Security
- No hardcoded API keys or secrets in source code
- All credentials loaded from environment variables via Settings class
- Bandit security scan configuration (B101, B601 skipped appropriately)

### Documentation
- README.md: Complete rewrite with architecture diagram, features table, quick start
- RELEASE_NOTES.md: Comprehensive v1.0.0 release notes
- FINAL_RELEASE_REPORT.md: Complete verification audit
- LICENSE: MIT License added

## [Unreleased]

### Planned
- CHANGELOG.md (this file) maintenance
- GitHub Actions CI/CD workflow
- Dockerfile and docker-compose.yml
- PyPI package publishing
- Test coverage reporting (Codecov/CodeClimate)
- Redis/persistent cache integration
- Authentication layer (API keys, OAuth)
- LLM streaming integration with MCP
- More financial tools (portfolio, screening, options)
- WebSocket support for real-time data

---

## Release Process

1. Update version in `pyproject.toml` and `mcp_server/config/settings.py`
2. Update CHANGELOG.md with new version section
3. Run full test suite: `pytest tests/ -q`
4. Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
5. Push tag: `git push origin v1.0.0`
6. GitHub Actions builds and publishes to PyPI (when configured)
6. Create GitHub Release with RELEASE_NOTES.md content

---

**Version:** 1.0.0  
**Date:** 2024-07-23  
**Status:** Production Ready ✅