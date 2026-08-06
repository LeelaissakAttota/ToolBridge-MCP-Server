# User Guide

ToolBridge exposes seven MCP tools through one validated MCP endpoint and provides a read-only operational dashboard.

## Available tools

| Tool | Purpose | Important constraint |
| --- | --- | --- |
| `system_status` | Return service status | No input |
| `stock_price` | Retrieve a current quote | External market-data availability applies |
| `website_reader` | Extract clean text from a web page | Public HTTPS destinations only by default |
| `sql_query` | Run a bounded SQLite read query | Read-only `SELECT`/CTE access under configured root |
| `csv_analysis` | Inspect columns, preview, missing values, and statistics | Files must be under configured CSV root |
| `currency_converter` | Convert one amount to multiple currencies | Configured exchange-rate provider and cache apply |
| `hcl_curie_analysis` | Analyze or summarize text | Requires an enabled LLM provider |

## Connect an MCP client

Start ToolBridge and configure the client for Streamable HTTP at:

```text
http://127.0.0.1:8000/mcp/
```

The client can discover schemas with `tools/list` and invoke a tool with `tools/call`. Inputs and outputs are strictly validated. Tool failures use normalized, non-secret error responses.

## Configure LLM providers

Priority is Cerebras, NVIDIA, then OpenRouter by default. In `.env`, enable only approved providers and set the matching key and model. The router retries bounded failures and moves to the next configured provider when appropriate.

Provider prompts, credentials, and results never appear in operational logs or the dashboard.

## Use the dashboard

Open `http://127.0.0.1:8501` to view:

- version, uptime, lifecycle, and readiness
- provider configuration, health, failover, latency, usage, and estimated cost
- tool registration, health, executions, timing, and last execution
- aggregate request/error metrics
- bounded safe logs

The dashboard performs only read requests. Metrics and logs reset when the API process restarts.

## Safe operation

- Keep the API and dashboard on loopback.
- Treat website and LLM output as untrusted.
- Use only approved databases and CSV files.
- Confirm provider terms, privacy, quota, and costs before enabling external integrations.
- Never place keys in requests, source files, commits, or screenshots.
