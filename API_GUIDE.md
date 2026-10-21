# API Guide

The FastAPI control plane and MCP Streamable HTTP transport run in one process by default.

## HTTP endpoints

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| `GET` | `/` | Service identity and endpoint links | `200` |
| `GET` | `/health` | Process liveness | `200`, `status=ok` |
| `GET` | `/ready` | Local lifecycle and composition readiness | `200` when ready, otherwise `503` |
| `GET` | `/operations/snapshot` | Read-only secret-free dashboard model | `200` |
| `GET` | `/docs` | OpenAPI interface | `200` |
| MCP | `/mcp/` | Streamable HTTP MCP protocol | protocol response |

`/health` deliberately avoids provider calls. `/ready` checks local initialization and configured policy without spending provider quota. The monitoring snapshot never includes prompts, tool inputs/results, URLs, SQL, file paths, credentials, or authorization headers.

The operations snapshot includes additive `providers` and `models` collections with normalized capabilities, active selection/reason, availability, health/latency, request/error/retry/success metrics, model discovery/cache timing, configured budget limits, and estimated process-local cost. It remains a read-only allowlisted projection.

## MCP lifecycle

1. Send `initialize` with a supported MCP protocol version.
2. Discover tools with `tools/list`.
3. Execute a discovered tool with `tools/call` and schema-valid arguments.
4. Inspect `isError`, text content, and validated structured content.

Example discovery request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

Required headers are `Content-Type: application/json` and `Accept: application/json, text/event-stream`.

## Error behavior

MCP Core normalizes unknown tools, invalid requests, timeouts, cancellations, execution failures, and invalid responses. Provider errors are categorized as timeout, authentication, rate limit, unavailable, invalid request/response, budget exceeded, capability unavailable, or internal failure. Logs retain category and request ID, not sensitive payloads.

## Compatibility

- ToolBridge version: `1.1.0`
- Python: `3.12`
- MCP SDK: `1.29.0`
- Transport: Streamable HTTP

Tool schemas returned by discovery are the authoritative invocation contract.
