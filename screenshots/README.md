# Screenshot Checklist

No screenshots were present when the v1.1.0 recruiter package was prepared. The owner should capture real output from the released application; do not substitute mockups or generated UI images.

## Recommended Screenshots

### 1. Dashboard Overview

Capture the Streamlit **Overview** tab showing:

- ToolBridge Operations title
- version `1.1.0`
- healthy lifecycle state
- readiness checks
- a clean browser crop focused on the application

### 2. Health Response

Capture `GET http://127.0.0.1:8000/health` showing HTTP 200 and the small `status`, `service`, and `environment` response.

### 3. Readiness Response

Capture `GET http://127.0.0.1:8000/ready` showing HTTP 200, `ready=true`, and the lifecycle, registry, tool-lifecycle, and provider-router checks.

### 4. MCP Tool Discovery

Capture `tools/list` with all seven tool names visible. Include enough schema context to demonstrate discovery, but avoid an unreadably long terminal dump.

### 5. Successful `system_status`

Capture the MCP `tools/call` result showing `isError=false` and structured `service`, `status`, and `timestamp` fields.

### 6. Provider Dashboard

Capture the Streamlit **Providers** tab showing Cerebras, NVIDIA, and OpenRouter discovery/status, capability information, and failover state. It is truthful for providers to show disabled or unconfigured; do not enable them solely for a screenshot.

### 7. Architecture Diagram

Optionally render the Mermaid diagram in [ARCHITECTURE.md](../ARCHITECTURE.md) or the README. Capture the MCP/tool flow and provider routing flow at a readable size.

## Capture Safety

Before saving each screenshot, verify that it does **not** show:

- API keys, tokens, passwords, cookies, authorization headers, or `.env` contents
- usernames, home-directory names, personal/local filesystem paths, or private repository URLs
- prompts, source text, tool arguments/results containing private data, SQL, database contents, CSV cells, or website content
- provider account details, quota/billing pages, request identifiers that should remain private, or raw provider responses
- unrelated applications, browser tabs, notifications, email/chat content, clocks/calendars if privacy-sensitive, or desktop files

Use a dedicated local browser window and terminal. Crop to the relevant application or response. Prefer JSON pretty-printing and a readable font size. Review the final image at full resolution before adding it to Git.

## Suggested Filenames

```text
screenshots/dashboard-overview.png
screenshots/health-response.png
screenshots/readiness-response.png
screenshots/mcp-tools-list.png
screenshots/system-status-call.png
screenshots/provider-dashboard.png
screenshots/architecture.png
```

Only add the files that were actually captured and reviewed.

