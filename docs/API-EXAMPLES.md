# HTTP and MCP Examples

These examples target the released local endpoint at `127.0.0.1:8000`. Start the service first:

```powershell
.\.venv\Scripts\python.exe -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

All MCP examples use the release's stateless JSON Streamable HTTP configuration. Required request headers are `Content-Type: application/json` and `Accept: application/json, text/event-stream`.

## HTTP Interfaces

### Service identity

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
```

Stable response fields are `name`, `version`, `status`, `health`, `readiness`, `operations`, `mcp`, and `docs`.

### Liveness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Successful liveness returns HTTP 200 with `status=ok`, `service=toolbridge-mcp`, and the configured environment name. It does not call external systems.

### Readiness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready | ConvertTo-Json -Depth 6
```

Ready state returns HTTP 200 with `status=ready`, `ready=true`, a runtime timestamp, and checks for `lifecycle`, `registry`, `tool_lifecycle`, and `provider_router`. A non-ready process returns HTTP 503 with the same response model.

### Operations snapshot

```powershell
Invoke-RestMethod http://127.0.0.1:8000/operations/snapshot |
  ConvertTo-Json -Depth 12
```

The exact top-level fields are `system`, `readiness`, `providers`, `models`, `tools`, `metrics`, `costs`, and `logs`. This projection is read-only and explicitly excludes prompts, tool inputs/results, URLs, SQL, parameters, file paths, credentials, authorization headers, and raw external responses.

## MCP Initialize

Using the checked-in request body:

```powershell
$mcpHeaders = @{ Accept = 'application/json, text/event-stream' }
$initialize = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_initialize_request.json
$initialize | ConvertTo-Json -Depth 10
```

Equivalent request body:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {
      "name": "toolbridge-demo",
      "version": "1.0"
    }
  }
}
```

The result returns the negotiated `protocolVersion`, server information, instructions, and capabilities. The release advertises `capabilities.tools.listChanged=false`.

## MCP `tools/list`

```powershell
$tools = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_tools_list_request.json
$tools.result.tools | Select-Object name, description
```

The verified discovery order is:

```text
csv_analysis
currency_converter
hcl_curie_analysis
sql_query
stock_price
system_status
website_reader
```

Each entry also includes authoritative `inputSchema` and `outputSchema` objects.

## MCP `tools/call`: `system_status`

```powershell
$status = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_system_status_request.json
$status.result.structuredContent | ConvertTo-Json
```

The verified structured result has:

- `service`: constant `toolbridge-mcp`
- `status`: constant `ok`
- `timestamp`: runtime-generated ISO 8601 string

`result.isError` is `false` on success.

## MCP `tools/call`: Safe SQL

The default release configuration uses an isolated in-memory SQLite database, allowing a deterministic read-only demonstration:

```powershell
$sql = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_sql_query_request.json
$sql.result.structuredContent | ConvertTo-Json -Depth 6
```

The request executes `SELECT 1 AS value` with a separate empty parameter object. The verified structured response reports column `value`, one row containing numeric value `1`, `row_count=1`, `truncated=false`, and a runtime-measured `execution_ms`.

For a configured file database, use named parameters rather than interpolating values:

```json
{
  "name": "sql_query",
  "arguments": {
    "query": "SELECT name, quantity FROM items WHERE quantity >= :minimum ORDER BY quantity",
    "parameters": {
      "minimum": 2
    },
    "max_rows": 25
  }
}
```

Only use this form when the approved configured SQLite database and table actually exist.

## Representative Invalid Tool

```powershell
$invalid = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/mcp/ `
  -Headers $mcpHeaders `
  -ContentType 'application/json' `
  -InFile examples/mcp_invalid_tool_request.json
$invalid.result | ConvertTo-Json -Depth 6
```

The MCP request itself returns HTTP 200 with a tool result where `isError=true` and text identifies the unknown tool. No server crash or configuration disclosure occurs.

An unsafe SQL operation such as `DELETE FROM example` is rejected during typed input validation before execution. Application-level failures use a normalized non-secret error containing a stable code, correlation identifier, bounded safe details, message, and retryability.

## `curl.exe` Alternative

The checked-in JSON bodies also work with Windows curl:

```powershell
curl.exe -sS http://127.0.0.1:8000/mcp/ `
  -H "Content-Type: application/json" `
  -H "Accept: application/json, text/event-stream" `
  --data-binary "@examples/mcp_tools_list_request.json"
```

## Network- and Provider-Dependent Tools

The following are real interfaces but are intentionally not represented with fabricated successful responses:

- `stock_price`: requires an available configured public market-data provider
- `website_reader`: requires permitted public HTTPS network access and a safe destination
- `currency_converter`: requires the Frankfurter endpoint to be reachable
- `hcl_curie_analysis`: requires an enabled Cerebras, NVIDIA, or OpenRouter provider with credentials and an approved model
- `csv_analysis`: requires an approved CSV beneath the configured root

Consult `tools/list` for current schemas and [USER_GUIDE.md](../USER_GUIDE.md) for operating constraints.

