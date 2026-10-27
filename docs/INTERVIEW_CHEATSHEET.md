# Interview cheat sheet

One page. Say this. Do not read the repository aloud.

## One sentence

ToolBridge is a local MCP server that lets an AI client discover and call seven bounded tools, with validation in front and vendor details behind adapters.

## Tools

| Tool | What it does |
| --- | --- |
| `system_status` | Returns local service status. No network. |
| `sql_query` | Runs one read-only `SELECT` or CTE. SQLite by default. |
| `csv_analysis` | Summarizes a CSV under the configured root. |
| `website_reader` | Reads a public HTTPS page, with size and destination checks. |
| `stock_price` | Gets one market quote from a configured provider. |
| `currency_converter` | Converts one amount into several currencies. |
| `llm_analysis` | Analyzes or summarizes text through the provider router. |

## Security boundaries

- SQL is read-only. A `DELETE` is rejected before the database runs. Parameters are bound, not pasted into the query.
- The dashboard and logs do not show prompts, SQL, tool results, paths, or API keys.
- Docker publishes only on `127.0.0.1`. There is no full login system. Do not put this on the public internet.
- Optional MCP bearer token: `TOOLBRIDGE_MCP_AUTH_TOKEN`. If it is set, `/mcp/` returns 401 without `Authorization: Bearer`.

## Architecture in five lines

1. An MCP client talks to FastAPI and FastMCP on one process.
2. The tool executor validates input, enforces a timeout, and calls a registered tool.
3. Tools depend on ports. SQLite, optional PostgreSQL, HTTP, and files are adapters.
4. `llm_analysis` goes through a provider router: capability, budget, retry, then failover.
5. A read-only Streamlit dashboard reads `GET /operations/snapshot`. It does not run tools by itself.

## Tests and demo path

- Tests: **239 passed**, **1 skipped**. The skip is the live PostgreSQL test. It runs only if `TOOLBRIDGE_TEST_POSTGRES_DSN` is set.
- Product version on `GET /` is `1.1.0`. MCP `initialize` may show SDK version `1.29.0`. Those are different numbers.
- Demo script: [DEMO.md](DEMO.md). Gallery: [../screenshots/README.md](../screenshots/README.md).
- Basic demo stays on SQLite (`data/demo.db`). PostgreSQL is optional. Do not start Postgres for the five-minute demo.

## Start in under two minutes

From the repository root, two PowerShell windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

```powershell
.\.venv\Scripts\python.exe -m streamlit run toolbridge/dashboard/app.py --server.address 127.0.0.1 --server.port 8501
```

Then open `http://127.0.0.1:8000/health` and `http://127.0.0.1:8501`. If `8501` is already taken, use another loopback port for the dashboard and keep the API on port `8000`.

If `.venv` is missing, use the Windows steps in the [README](../README.md). If a provider is enabled in `.env`, startup may call that provider. That is not required for the demo.
