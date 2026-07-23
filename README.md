# ToolBridge MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests Passing](https://img.shields.io/badge/tests-344%20passing-brightgreen.svg)](https://github.com/LeelaissakAttota/toolbridge-mcp-server/actions)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A production-ready **Model Context Protocol (MCP) Server** with enterprise-grade financial intelligence tools. Built with clean architecture, SOLID principles, and full async/await support.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ToolBridge MCP Server                        │
├─────────────────────────────────────────────────────────────────┤
│  Interface Layer (MCP Tools)                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Stock    │ │ Currency │ │Historical│ │ Technical         │  │
│  │ Price    │ │ Exchange │ │ Price    │ │ Indicators        │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Company  │ │ Market   │ │Financial │ │ News              │  │
│  │ Info     │ │ Movers   │ │ Analysis │ │ Sentiment         │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Application Layer (Services)                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐   │
│  │ FinanceService  │  │ CurrencyService │  │ ProviderRouter│   │
│  └─────────────────┘  └─────────────────┘  └───────────────┘   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐   │
│  │ HealthMonitor   │  │ MetricsCollector│  │ FinanceCache  │   │
│  └─────────────────┘  └─────────────────┘  └───────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  Infrastructure Layer (Providers)                               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │ Yahoo      │ │ Alpha      │ │ Twelve     │ │ Finnhub    │   │
│  │ Finance    │ │ Vantage    │ │ Data       │ │            │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│  │ Frankfurter│ │ExchangeRate│ │Currency    │                 │
│  │ (ECB)      │ │-API        │ │Layer       │                 │
│  └────────────┘ └────────────┘ └────────────┘                 │
├─────────────────────────────────────────────────────────────────┤
│  Domain Layer (Models, Exceptions, Base Interfaces)             │
└─────────────────────────────────────────────────────────────────┘
```

## ✨ Features

### 📈 Stock Market Tools (7 MCP Tools)
| Tool | Description |
|------|-------------|
| `stock_price` | Real-time quotes with company info, OHLC, volume, market cap |
| `historical_price` | OHLCV data, multiple intervals, date ranges, adjusted close |
| `company_info` | Profile, financials, leadership, key stats, dividends |
| `market_movers` | Gainers, losers, most active, trending, market summary |
| `technical_indicators` | SMA, EMA, RSI, MACD, Bollinger, ATR, VWAP, crossovers, S/R, trend |
| `financial_news` | Company/market/sector news with filters |
| `news_sentiment` | LLM-powered sentiment analysis (bullish/bearish/neutral) |
| `financial_analysis` | Comprehensive LLM-generated investment reports |

### 💱 Currency Tools (3 MCP Tools)
| Tool | Description |
|------|-------------|
| `currency_exchange` | Convert currencies, latest/historical rates |
| `supported_currencies` | List all supported currency codes with names/symbols |

### 🔄 Provider Failover (Automatic)
| Priority | Stock Providers | Currency Providers |
|----------|-----------------|-------------------|
| 1 | Yahoo Finance (free) | Frankfurter/ECB (free) |
| 2 | Alpha Vantage (free tier) | ExchangeRate-API (free tier) |
| 3 | Twelve Data (free tier) | CurrencyLayer (free tier) |
| 4 | Finnhub (free tier) | - |
| 5 | Polygon (optional) | - |

### 🤖 LLM Provider Layer
| Provider | Models |
|----------|--------|
| Cerebras | llama3.1-8b, 70b, 405b |
| NVIDIA NIM | Various |
| OpenRouter | Claude, GPT, Llama, etc. |

### 🏗️ Enterprise Features
- **Clean Architecture** - Domain, Application, Infrastructure, Interface layers
- **SOLID Principles** - All components follow SRP, OCP, LSP, ISP, DIP
- **Async/Await** - Full async implementation for high concurrency
- **Provider Failover** - Automatic with health monitoring, circuit breaker, exponential backoff
- **TTL Caching** - Multi-tier (30s stock, 5min currency, 24h currencies)
- **Health Monitoring** - Background checks with Prometheus-style metrics
- **Retry Logic** - Configurable retries with exponential backoff (max 3)
- **Schema Validation** - JSON Schema Draft 2020-12 for all tool I/O
- **Type Safety** - Complete type hints, Pydantic v2 models

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/LeelaissakAttota/toolbridge-mcp-server.git
cd toolbridge-mcp-server

# Setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python -m mcp_server.server
```

## 🔧 Configuration

Create `.env` with your API keys:

```bash
# LLM Providers (at least one required)
CEREBRAS_API_KEY=your_key
NVIDIA_API_KEY=your_key
OPENROUTER_API_KEY=your_key

# Optional: Finance provider keys (free tiers available)
ALPHA_VANTAGE_API_KEY=your_key
TWELVE_DATA_API_KEY=your_key

# Provider Routing
DEFAULT_PROVIDER=openrouter
DEFAULT_MODEL=claude-3.5-sonnet
ENABLE_FAILOVER=true

# Cache & Performance
CACHE_TTL=300
REQUEST_TIMEOUT=30
MAX_RETRIES=3
ENABLE_CACHE=true
ENABLE_HEALTH_MONITOR=true
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -q

# Run with coverage
pytest tests/ --cov=mcp_server --cov-report=html

# Run specific module
pytest tests/test_technical_indicators_tool.py -v

# Output: 344 passed, 2 warnings in ~5s
```

## 📊 Test Coverage

| Phase | Tests | Description |
|-------|-------|-------------|
| Phase 1 (Foundation) | ~50 | Config, logging, models, base provider |
| Phase 2 (MCP Core) | ~100 | Tools, registry, validation, server |
| Phase 3 (Provider Layer) | ~104 | Provider abstraction, routing, failover |
| Sprint 4.1 (Finance Services) | ~17 | Cache, finance service, currency service |
| Sprint 4.2 (Advanced Finance) | ~73 | 7 new financial intelligence tools |
| **Total** | **344** | **100% passing** |

## 📦 Requirements

- Python 3.11+
- Dependencies (auto-installed):
  - `pydantic>=2.0,<3.0` - Settings & validation
  - `pydantic-settings>=2.0,<3.0` - Environment config
  - `uvicorn[standard]>=0.23` - ASGI server
  - `mcp>=1.0.0` - Model Context Protocol
  - `jsonschema>=4.0,<5.0` - Schema validation
  - `numpy>=1.24.0` - Technical indicators
  - `aiohttp>=3.8.0` - HTTP client

## 🏗️ Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Format code
ruff check . --fix
black .

# Type check
mypy mcp_server

# Security scan
bandit -r mcp_server

# Run tests
pytest tests/ -q
```

## 📁 Project Structure

```
toolbridge-mcp-server/
├── mcp_server/
│   ├── config/          # Settings, environment config
│   ├── core/            # Health, server core
│   ├── exceptions/      # Exception hierarchy
│   ├── health/          # Health checks
│   ├── logging/         # Structured logging
│   ├── mcp_core/        # MCP protocol errors
│   ├── models/          # Base Pydantic models
│   ├── providers/       # LLM & Finance providers
│   ├── services/        # Finance, Currency services
│   ├── tools/           # MCP tools (10 finance tools)
│   ├── validation/      # Schema validation
│   └── server.py        # FastMCP entry point
├── tests/               # 344 tests (100% passing)
├── docs/                # Documentation
├── docker/              # Docker configs (future)
├── scripts/             # Helper scripts
├── LICENSE              # MIT License
├── pyproject.toml       # Build & tool config
├── requirements.txt     # Runtime dependencies
└── README.md            # This file
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`pytest tests/ -q`)
5. Submit PR with description

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/LeelaissakAttota/toolbridge-mcp-server/issues)
- **Discussions:** [GitHub Discussions](https://github.com/LeelaissakAttota/toolbridge-mcp-server/discussions)

---

**ToolBridge MCP Server v1.0.0** - *Empowering AI with Professional Financial Intelligence*