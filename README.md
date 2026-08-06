# ToolBridge MCP Server

ToolBridge is a Model Context Protocol (MCP) service with typed, validated, observable tools. Version `0.4.0` completes Phase 4 implementation: a reusable tool framework and the first read-only production tool, `stock_price`.

Phase 4 is implemented and tested but remains uncommitted and awaits project-owner acceptance. Dashboard, agents, authentication, CI/CD, deployment, and later phases are not implemented.

## Current capabilities

- FastAPI control plane and stateless FastMCP Streamable HTTP transport
- Framework-independent MCP registry, discovery, validation, execution, and normalized errors
- Reusable `BaseTool` lifecycle and automatic registry integration
- Structured allowlisted logging, in-process metrics, and typed health snapshots
- `system_status` diagnostic tool
- `stock_price` with Yahoo Finance primary and optional Alpha Vantage fallback
- Bounded per-symbol caching, retries, exponential backoff, and failover
- Provider-neutral LLM routing for Cerebras, NVIDIA, and OpenRouter
- Offline tests using fakes and `httpx.MockTransport`

## Setup and local run

Requirements: Python 3.12, internet access for installation and live stock requests, an Alpha Vantage key only when that fallback is enabled, and LLM credentials only for enabled LLM providers.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m pytest -q -p no:cacheprovider
python -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

The `.env` copy is optional. Startup and the default tests perform no external data requests.

| Purpose | URL |
| --- | --- |
| Service metadata | <http://127.0.0.1:8000/> |
| Liveness | <http://127.0.0.1:8000/health> |
| OpenAPI | <http://127.0.0.1:8000/docs> |
| MCP Streamable HTTP | `http://127.0.0.1:8000/mcp/` |

The MCP trailing slash is intentional. `/health` never calls external providers.

## MCP tools

### `system_status`

Accepts no arguments and returns the service identifier, `ok` status, and an ISO 8601 timestamp.

### `stock_price`

Input: `{"symbol": "NVDA"}`

Symbols are trimmed, uppercased, length-bounded, and restricted to letters, numbers, periods, and hyphens before outbound requests.

The normalized response contains `symbol`, `current_price`, `company_name`, `currency`, `exchange`, `day_high`, `day_low`, `open`, `previous_close`, `market_status`, `timestamp`, `provider`, and `cached`. Optional fields are null when the selected source does not supply them; ToolBridge never invents market metadata.

## Stock configuration

Common settings use the `TOOLBRIDGE_STOCK_PRICE__` prefix.

| Suffix | Default | Purpose |
| --- | --- | --- |
| `ENABLED` | `true` | Register the tool |
| `TIMEOUT_SECONDS` | `10` | Whole-tool and HTTP timeout |
| `RETRY_COUNT` | `2` | Additional attempts per provider |
| `CACHE_DURATION_SECONDS` | `60` | Per-symbol cache lifetime |
| `MAX_CACHE_ENTRIES` | `256` | Cache memory bound |
| `PROVIDER_PRIORITY` | `yahoo_finance,alpha_vantage` | Provider order |
| `RETRY_BACKOFF_SECONDS` | `0.1` | Initial retry delay |
| `MAX_RETRY_BACKOFF_SECONDS` | `1` | Retry-delay cap |
| `MAX_PROVIDER_RESPONSE_BYTES` | `1048576` | Upstream body limit |
| `HEALTH_CHECK_SYMBOL` | `MSFT` | Explicit probe symbol |

Yahoo settings use `TOOLBRIDGE_STOCK_PRICE__YAHOO_FINANCE__`; Alpha Vantage uses `TOOLBRIDGE_STOCK_PRICE__ALPHA_VANTAGE__`. Base URLs must be safe HTTPS origins, and configured paths cannot override authorities or traverse directories. See [.env.example](.env.example).

Alpha Vantage requires `ENABLED=true` and `API_KEY`. Its documented `GLOBAL_QUOTE` supplies price and OHLC data but not company name, currency, exchange, or live per-symbol market state, so those fields are null or `unknown`. Standard quotes may be end-of-day unless an applicable entitlement is used. See the [official Alpha Vantage documentation](https://www.alphavantage.co/documentation/).

Yahoo Finance is the credential-free primary because its chart response supplies broader metadata. The chart endpoint is not a documented, supported public API contract and may change. Review the [Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) and obtain an approved data license before commercial or production use.

## Architecture

```text
BaseTool
   |
   v
ToolManager --> ToolRegistry --> input validation --> execution
                                                   |
                                                   v
                                  response validation --> logs --> metrics
```

Tool domain and application code does not import FastAPI or FastMCP. Provider HTTP mapping is isolated in adapters; configuration, logging, and composition are infrastructure concerns. Each tool is independently registrable, testable, health-checkable, and closable.

```text
toolbridge/
|-- core/                    MCP contracts, registry, validation, executor
|-- adapters/                FastMCP and execution-log adapters
|-- providers/               Phase 3 LLM router layers
|-- tools/
|   |-- domain/              Health, metrics, stock models, errors
|   |-- application/         BaseTool, manager, metrics, stock routing
|   |-- adapters/            Yahoo Finance and Alpha Vantage
|   `-- infrastructure/      Factory and stock logging
|-- bootstrap.py
|-- config.py
`-- main.py

tests/
|-- unit/providers/
|-- unit/tools/
|-- unit/
`-- test_api.py
```

## Tests

```powershell
python -m pytest -q -p no:cacheprovider
python -m pip check
```

Current result: **75 passed** on 2026-08-06. The offline suite covers registration, MCP discovery, success, invalid symbols, retries, failover, caching, network failures, timeouts, response validation, health, metrics, adapters, configuration, and log redaction. One third-party `StarletteDeprecationWarning` remains. No line-coverage package is installed, so no numerical coverage claim is made.

## Documentation

- [Project status](PROJECT_STATUS.md)
- [Project rules](PROJECT_RULES.md)
- [Roadmap](ROADMAP.md)
- [Architecture](ARCHITECTURE.md)
- [Tasks](TASKS.md)
- [Changelog](CHANGELOG.md)
- [Coding standards](CODING_STANDARDS.md)
- [Testing strategy](TESTING_STRATEGY.md)
- [Git workflow](GIT_WORKFLOW.md)
- [Deployment plan](DEPLOYMENT_PLAN.md)
- [Security guidelines](SECURITY_GUIDELINES.md)
- [Decision log](DECISIONS.md)

## Current limitations

Stock data is informational, not financial advice. Yahoo licensing and its undocumented schema require approval before production. Alpha Vantage may be end-of-day and omits some metadata. Cache and metrics are process-local. Health checks are on demand. Authentication, authorization, rate limiting, persistence, agents, dashboard, packaging, deployment, and CI/CD remain unimplemented. The service is local-development only.

## License

No software license has been selected. Until one is added, no permission to copy, modify, or redistribute the project is granted by default.
