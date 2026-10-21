# Supervised-control pages (Deep Research, Equity Research)

The dashboard has two extra pages, **Deep Research Control** and **Equity Research Control**.
They call each project's local control API (see `docs/CONTROL_API.md` in those repos).

Configure (tokens must match the ones the control APIs were started with):

```bash
export TOOLBRIDGE_CONTROL_DEEP_RESEARCH_URL=http://127.0.0.1:8711     # default
export TOOLBRIDGE_CONTROL_DEEP_RESEARCH_TOKEN=...                      # >= 16 chars
export TOOLBRIDGE_CONTROL_EQUITY_RESEARCH_URL=http://127.0.0.1:8712   # default
export TOOLBRIDGE_CONTROL_EQUITY_RESEARCH_TOKEN=...
```

URLs must be loopback. Each page has: approval-policy toggles (approval mode,
auto-approve low-risk), start run, live status (2 s refresh), pause/resume/stop,
pending approvals with risk badge and editable inputs (approve/override/reject),
steps table, override & re-run, live logs with errors, an approval feed
(AUTO = blue, MANUAL = green, REJECTED = red), and masked API-key management
(write-only password field; values are never shown or logged).
