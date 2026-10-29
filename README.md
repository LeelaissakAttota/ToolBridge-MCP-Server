# ToolBridge MCP Server

![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/Protocol-MCP-111827?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-239%20passing-2EA44F?style=for-the-badge)
![License MIT](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**One interface for AI assistants to discover and use tools for APIs, local data, and text analysis.**

ToolBridge is a Python project that exposes seven tools through the Model Context Protocol (MCP). It validates requests, keeps data access bounded, and routes text analysis through interchangeable LLM providers. A read-only dashboard shows service health and execution metrics.

**Version:** v1.1.0 | **Python:** 3.12 | **Tests:** 239 passing, 1 skipped | **License:** MIT | **Deployment:** local or trusted single-host

[Demo walkthrough](docs/DEMO.md) | [Architecture](ARCHITECTURE.md) | [Installation](docs/INSTALLATION.md) | [Screenshot gallery](screenshots/README.md)

## The problem it solves

Connecting an AI assistant to a database, a website, and a model provider often means writing separate integration code for each dependency. Validation, error handling, and vendor-specific behavior can become tangled together.

ToolBridge gives compatible clients a shared way to discover tools and call them with structured arguments. Behind that interface, each tool owns a bounded task, and provider adapters keep vendor details separate from application logic.

For example, a client can discover `sql_query`, submit a read-only query, and receive structured rows. An attempted SQL write is rejected before database execution. The dashboard shows operational activity without displaying the query or its result.

## See it working

[![ToolBridge demo video](https://img.youtube.com/vi/A4pQcOFKYcA/maxresdefault.jpg)](https://youtu.be/A4pQcOFKYcA)

**[▶ Watch Demo](https://youtu.be/A4pQcOFKYcA)**

**Claude Desktop calling ToolBridge through the stdio bridge** (`Convert $100 into Rupees and Euros` → `currency_converter`)

![Claude Desktop using the ToolBridge currency converter tool](docs/images/claude-desktop-toolbridge.png)

| Tool Playground | Guided provider setup |
| --- | --- |
| ![Tool Playground running a read-only SQL query](docs/images/playground-sql.png) | ![Guided LLM provider setup with Auto (cheapest) model selection](docs/images/guided-provider-setup.png) |
| Any tool, run through the real MCP endpoint, with readable results and raw JSON. | Paste a key once (never shown again), pick Auto (cheapest) or a model, test, save. |

The [evidence gallery](screenshots/README.md) adds seven-tool discovery, SQL write rejection, and captured live NVIDIA, stock-price, and currency-conversion results (point-in-time captures).

| Operations | Seven tools | SQL write rejected |
| --- | --- | --- |
| ![ToolBridge operations overview](screenshots/01-dashboard-overview.png) | ![ToolBridge MCP tool dashboard](screenshots/04-mcp-tools.png) | ![SQL write operation rejected](screenshots/12-sql-write-operation-rejected.png) |

More captures, with what each one proves: [screenshot gallery](screenshots/README.md) (`02` health, `03` readiness, `05` system status, `06` provider platform, `08` NVIDIA live test, `09` health and readiness, `10` stock price, `11` currency converter).

## What I built

- **A discoverable tool interface:** FastAPI and FastMCP expose seven tools with strict Pydantic input/output schemas and normalized failures.
- **Bounded data access:** read-only SQL controls, confined CSV paths, website destination checks, timeouts, and response limits.
- **A provider plugin layer:** Cerebras, NVIDIA, and OpenRouter adapters share provider-neutral contracts, with capability-aware routing, bounded retries, failover, and estimated budget controls.
- **Operational visibility:** health and readiness endpoints plus a read-only Streamlit dashboard that excludes prompts, tool payloads, and credentials.
- **Tool Playground:** a dashboard page that runs any tool through the real MCP endpoint (JSON-RPC `tools/call`), with demo examples, plain-language-to-SQL, CSV upload, and text or audio input for `llm_analysis`.
- **Guided provider setup with auto model choice:** pick OpenRouter, OpenAI, Anthropic, Gemini, Groq, Cerebras, NVIDIA, or any OpenAI-compatible endpoint, paste the key once (write-only), and let **Auto (cheapest)** pick the cheapest working model, free models first.
- **LLM analysis:** `llm_analysis` analyzes or summarizes untrusted text through the provider router, with retries, failover, and budget limits.
- **Claude Desktop stdio bridge:** `python -m toolbridge.stdio_bridge` relays MCP from Claude Desktop (or any stdio MCP client) to the running server, so desktop calls also appear in History and Logs.
- **Demo data and logs:** fictional SQL/CSV/text samples plus 12 success and 10 error requests in `examples/demo-data`; History and Logs pages show sanitized activity only.
- **Repeatable validation and packaging:** 239 passing automated tests (1 live PostgreSQL test skipped unless a database is configured), GitHub Actions checks, and a non-root Docker/Compose setup.

## Available tools

| Tool | What it does | Dependency or boundary |
| --- | --- | --- |
| 🩺 `system_status` | Returns local service status | No external dependency |
| 🗄️ `sql_query` | Returns bounded read-only query results | PostgreSQL only. Read-only role, bound parameters, row and time limits. |
| 📊 `csv_analysis` | Summarizes a configured local CSV | Confined file paths and size limits |
| 🌐 `website_reader` | Extracts bounded text from a web page | Public HTTPS destinations by default |
| 📈 `stock_price` | Retrieves a market quote | External market-data service |
| 💱 `currency_converter` | Converts an amount to multiple currencies | External exchange-rate service |
| 🧠 `llm_analysis` | Analyzes or summarizes text | An enabled LLM provider |

MCP `tools/list` returns the authoritative input and output schemas. LLM providers are disabled by default; enabling one requires configuration and credentials.

## How it works

```mermaid
flowchart TD
    Client["MCP client"] --> API["FastAPI / FastMCP"]
    API --> Executor["Tool registry + validated execution"]
    Executor --> Data["HTTP / read-only PostgreSQL / CSV tools"]
    Executor --> Analysis["Text analysis tool"]
    Analysis --> Router["Provider routing + budgets + failover"]
    Router --> Providers["Cerebras / NVIDIA / OpenRouter"]
    Executor --> Operations["Safe operational state"]
    Router --> Operations
    Operations --> Snapshot["GET /operations/snapshot"]
    Snapshot --> Dashboard["Read-only Streamlit dashboard"]
```

The code follows Clean Architecture: domain and application logic sit inside replaceable adapters and infrastructure. Provider adapters translate vendor behavior into shared application contracts. See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed flows.

### Design decisions and tradeoffs

| Decision | Why it helps | Tradeoff |
| --- | --- | --- |
| Strict schemas and bounded execution | Reject malformed requests and limit resource use | Clients must follow explicit contracts |
| Read-only SQL | Supports analysis while restricting mutation | Conservative validation rejects some valid complex queries |
| Provider-neutral interfaces | Keep vendor details out of routing and tools | Each adapter must normalize vendor behavior |
| Process-local operational state | Keeps the single-process setup simple | Metrics and budget estimates reset on restart |
| Loopback-only deployment | Supports local use within the current security boundary | Public access requires additional controls |

## Install on a Windows laptop

These steps match [INSTALLATION.md](docs/INSTALLATION.md). You need Git and Python 3.12. Open PowerShell. If activation is blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that window only.

**1. Clone**

```powershell
git clone https://github.com/LeelaissakAttota/ToolBridge-MCP-Server.git
cd ToolBridge-MCP-Server
```

**2. Create the virtual environment**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --requirement requirements-dev.txt
python -m pip check
Copy-Item .env.example .env
```

Copying `.env.example` to `.env` as-is works; blank values fall back to defaults. The example contains no secrets and keeps LLM providers disabled. Put real keys only in `.env`. That file is gitignored.

**3. Set up PostgreSQL (needed only for `sql_query`)**

`sql_query` uses PostgreSQL only. The other six tools work without a database, so you can skip this step if you don't need SQL yet.

1. Install PostgreSQL 16 or newer from [postgresql.org](https://www.postgresql.org/download/windows/) and make sure the PostgreSQL service is running (Services app, or `Start-Service postgresql-x64-18` for version 18).
2. Open `psql` as the `postgres` superuser and create a read-only role and a database. Pick your own password:

```sql
CREATE ROLE toolbridge_ro LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE toolbridge;
\connect toolbridge
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE toolbridge TO toolbridge_ro;
GRANT USAGE ON SCHEMA public TO toolbridge_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO toolbridge_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO toolbridge_ro;
ALTER ROLE toolbridge_ro SET default_transaction_read_only = on;
```

3. Create your tables and load data as `postgres` (not as `toolbridge_ro`). The default privileges above let the read-only role select from new tables automatically.
4. Put the connection in your `.env` (never commit it):

```dotenv
TOOLBRIDGE_PHASE5__SQL_QUERY__BACKEND=postgres
TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_HOST=127.0.0.1
TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_PORT=5432
TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_DATABASE=toolbridge
TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_USER=toolbridge_ro
TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_PASSWORD=choose-a-password
TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_SSL=prefer
```

You can use a single `TOOLBRIDGE_PHASE5__SQL_QUERY__POSTGRES_DSN=postgresql://toolbridge_ro:choose-a-password@127.0.0.1:5432/toolbridge?sslmode=prefer` instead of the separate fields.

5. Check it: `psql -U toolbridge_ro -d toolbridge -c "SELECT 1"` should return `1`, and an `INSERT` as that role should fail with a read-only error. To run the one live PostgreSQL test, set `TOOLBRIDGE_TEST_POSTGRES_DSN` to the same DSN and run `python -m pytest tests/unit/tools/test_postgres_query.py`.

If PostgreSQL isn't running, `sql_query` returns a safe database error. There is no SQLite fallback.

**4. Start the API and MCP server**

Leave this window open. These commands assume Python 3.12 and the project `.venv` are already installed. Run them from the repository root in separate PowerShell terminals.

```powershell
.\.venv\Scripts\python.exe -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

**5. Start the dashboard**

```powershell
.\.venv\Scripts\python.exe -m streamlit run toolbridge/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

If you start the API on another host or port, point the dashboard at it with `TOOLBRIDGE_OPERATIONS__DASHBOARD_API_URL` (default `http://127.0.0.1:8000`).

Open the [dashboard](http://127.0.0.1:8501) or [API documentation](http://127.0.0.1:8000/docs). The MCP endpoint is `http://127.0.0.1:8000/mcp/`.

The [five-minute demo](docs/DEMO.md) includes startup settings for a credential-free walkthrough, copyable requests, and expected results. Docker Compose steps stay in [DEPLOYMENT.md](docs/DEPLOYMENT.md) and [INSTALLATION.md](docs/INSTALLATION.md).

**6. Connect Claude Desktop**

Keep the API running, then add this entry to Claude Desktop's `claude_desktop_config.json` (Settings → Developer → Edit config), adjusting the paths to your clone. A full example is in [examples/claude_desktop_config.example.json](examples/claude_desktop_config.example.json).

```json
{
  "mcpServers": {
    "toolbridge": {
      "command": "C:\\path\\to\\ToolBridge-MCP-Server\\.venv\\Scripts\\python.exe",
      "args": ["-m", "toolbridge.stdio_bridge"],
      "cwd": "C:\\path\\to\\ToolBridge-MCP-Server",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\ToolBridge-MCP-Server",
        "TOOLBRIDGE_BRIDGE_URL": "http://127.0.0.1:8000/mcp/"
      }
    }
  }
}
```

Restart Claude Desktop; `toolbridge` shows as **Running** and its seven tools become available. If `TOOLBRIDGE_MCP_AUTH_TOKEN` is set, the bridge reads it from the environment or the project `.env` and sends it as a Bearer token.

### Demo data

`sql_query` reads from PostgreSQL. A small fictional library dataset (`books`, 8 rows; `loans`, 10 rows) lives in [scripts/seed_postgres_demo.sql](scripts/seed_postgres_demo.sql). The script is idempotent and, if the `toolbridge_ro` role exists, grants it SELECT-only access. Run it once as the database owner or a superuser (never as `toolbridge_ro`):

```powershell
psql -U postgres -d toolbridge -f scripts/seed_postgres_demo.sql
```

`csv_analysis` uses `data/csv/sample_sales.csv` (60 orders, including one missing value) and `data/csv/sample_stock_prices.csv` (20 days of OHLCV for AAPL, RELIANCE.NS and NVDA). Regenerate them with `python scripts/seed_demo_data.py`.

Example MCP arguments:

```json
{"query": "SELECT b.title, l.member_name, l.loan_date FROM loans l JOIN books b ON b.book_id = l.book_id WHERE l.return_date IS NULL AND b.genre = :genre", "parameters": {"genre": "Technology"}}
{"relative_path": "sample_sales.csv", "preview_rows": 5}
```

More fictional samples (cafe-orders CSV, text samples, and ready-made MCP requests) live in [examples/demo-data](examples/demo-data/README.md); point `TOOLBRIDGE_PHASE5__CSV_ANALYSIS__ROOT_DIRECTORY` at it, and the dashboard follows the same value.

## Testing and evidence

The suite has **239 passing tests** and 1 skipped live PostgreSQL test, with no warnings, and Ruff lint/format checks pass. The tests cover validation, execution, provider routing, tool adapters, operations, the dashboard and Tool Playground helpers, `.env.example` loading, and an end-to-end stdio bridge check (a real MCP stdio client lists the seven tools and calls `system_status` through the bridge).

Reproduce the checks locally:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff format --check toolbridge tests scripts
.\.venv\Scripts\python.exe -m ruff check toolbridge tests scripts
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest tests
```

Captured manual evidence includes discovery of all seven tools, successful NVIDIA text analysis, AAPL market data, currency conversion, and SQL write rejection. Live results depend on upstream availability, configuration, and credentials where required. See the [evidence gallery](screenshots/README.md) and [testing strategy](docs/TESTING_STRATEGY.md).

GitHub Actions also checks startup, image builds, Compose configuration, and release smoke behavior. Tagged builds produce an image archive and SHA-256 artifact; they do not automatically publish or deploy it. The historical `v1.1.0` release is commit `4d8d73bb3ffa63102c7059429f14b459eb668546`; later screenshot captures are separate evidence.

## Current scope and limitations

ToolBridge supports local or trusted single-host use. Docker Compose publishes ports only on `127.0.0.1` and runs containers as non-root with read-only roots and restricted capabilities.

Apart from an optional shared MCP bearer token (`TOOLBRIDGE_MCP_AUTH_TOKEN`), there is no inbound authentication, authorization, tenant isolation, or application rate limiting, so the service must not be exposed directly to a public or untrusted network. Metrics, recent logs, health state, caches, and provider budget estimates are process-local and reset on restart. Estimated costs are not authoritative billing records.

Public deployment would require identity and access controls, rate limits, persistent audit/operational storage, and deployment-specific security review. See [KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) and [SECURITY.md](SECURITY.md).

## Documentation

| Looking for | Start here |
| --- | --- |
| A short working demonstration | [Demo walkthrough](docs/DEMO.md) |
| Technical design | [Architecture](ARCHITECTURE.md) |
| Setup and troubleshooting | [Installation](docs/INSTALLATION.md) and [troubleshooting](docs/TROUBLESHOOTING.md) |
| Request examples and contracts | [API examples](docs/API-EXAMPLES.md) and [API guide](docs/API_GUIDE.md) |
| Project summary | [Project summary](docs/PROJECT-SUMMARY.md) |
| Deployment details | [Deployment](docs/DEPLOYMENT.md) |
| Screenshot evidence | [Screenshot gallery](screenshots/README.md) |
