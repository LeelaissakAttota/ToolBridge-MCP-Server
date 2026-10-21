"""Optional inbound protection for the MCP transport.

Both features are opt-in: with no token and no extra hosts configured, the MCP
endpoint behaves exactly as before (loopback-only DNS-rebinding protection from
FastMCP and no authentication).
"""

from hmac import compare_digest

from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

_LOOPBACK_HOSTS = ("127.0.0.1:*", "localhost:*", "[::1]:*")
_LOOPBACK_ORIGINS = ("http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*")


def parse_csv_setting(value: str) -> tuple[str, ...]:
    """Split a comma-separated setting into unique, non-empty, trimmed entries."""

    seen: dict[str, None] = {}
    for part in value.split(","):
        if part.strip():
            seen.setdefault(part.strip(), None)
    return tuple(seen)


def build_transport_security(
    allowed_hosts: str, allowed_origins: str
) -> TransportSecuritySettings | None:
    """Return FastMCP transport security, or ``None`` to keep FastMCP's default.

    Configured hosts/origins are added to the loopback defaults, so local clients
    and the dashboard keep working when a reverse-proxy hostname is allowed.
    """

    hosts = parse_csv_setting(allowed_hosts)
    origins = parse_csv_setting(allowed_origins)
    if not hosts and not origins:
        return None
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[*_LOOPBACK_HOSTS, *hosts],
        allowed_origins=[*_LOOPBACK_ORIGINS, *origins],
    )


class BearerTokenMiddleware:
    """Require ``Authorization: Bearer <token>`` on every HTTP request it wraps."""

    def __init__(self, app: ASGIApp, token: str) -> None:
        if not token:
            raise ValueError("bearer token must not be empty")
        self._app = app
        self._expected = f"Bearer {token}".encode()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        supplied = b""
        for name, value in scope.get("headers", ()):
            if name == b"authorization":
                supplied = value
                break
        if not compare_digest(supplied, self._expected):
            await _unauthorized(send)
            return
        await self._app(scope, receive, send)


async def _unauthorized(send: Send) -> None:
    body = b'{"error":"unauthorized","message":"A valid bearer token is required."}'
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
                (b"www-authenticate", b'Bearer realm="toolbridge-mcp"'),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
