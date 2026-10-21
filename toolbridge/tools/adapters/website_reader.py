"""Safe asynchronous website retrieval and HTML boilerplate removal."""

import asyncio
import socket
from collections.abc import Awaitable, Callable, Iterable
from contextvars import ContextVar
from datetime import UTC, datetime
from html.parser import HTMLParser
from ipaddress import ip_address
from re import sub
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx

from toolbridge.tools.application.phase5_ports import WebsiteFetcher
from toolbridge.tools.domain.tool_errors import ExternalDataError, ExternalErrorCategory
from toolbridge.tools.domain.website import WebsiteDocument, normalize_https_url

HostResolver = Callable[[str], Awaitable[tuple[str, ...]]]

# Per-request host -> validated IP pins. A ContextVar keeps concurrent tool calls isolated.
_PINNED_ADDRESSES: ContextVar[dict[str, str] | None] = ContextVar(
    "toolbridge_website_pins", default=None
)


class PinnedNetworkBackend(httpcore.AsyncNetworkBackend):
    """Connect only to the IP address that passed destination validation.

    The URL host is still used for TLS SNI, certificate verification, and the Host
    header; only the TCP destination is replaced. This closes the DNS-rebinding
    window between validation-time and connect-time resolution.
    """

    def __init__(self, inner: httpcore.AsyncNetworkBackend | None = None) -> None:
        self._inner = inner or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        pins = _PINNED_ADDRESSES.get()
        address = pins.get(host.lower().rstrip(".")) if pins else None
        if address is None:
            raise httpcore.ConnectError("destination was not validated")
        return await self._inner.connect_tcp(
            address,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[httpcore.SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        raise httpcore.ConnectError("unix sockets are not permitted")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


def build_pinned_transport(
    network_backend: httpcore.AsyncNetworkBackend | None = None,
) -> httpx.AsyncHTTPTransport:
    """Build an httpx transport whose TCP connections honor validated IP pins."""

    transport = httpx.AsyncHTTPTransport()
    # httpx exposes no public network-backend option; replace its pool with an
    # equivalent public httpcore pool that uses the pinning backend.
    transport._pool = httpcore.AsyncConnectionPool(  # noqa: SLF001
        ssl_context=httpx.create_ssl_context(),
        network_backend=PinnedNetworkBackend(network_backend),
    )
    return transport


_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

_BOILERPLATE_TAGS = {
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "svg",
    "template",
}
_BLOCK_TAGS = {
    "article",
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "p",
    "pre",
    "section",
    "td",
    "th",
    "tr",
}


class _CleanTextParser(HTMLParser):
    """Small dependency-free extractor that omits common boilerplate regions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragments: list[str] = []
        self.title_fragments: list[str] = []
        self._ignored_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track ignored regions and block boundaries."""

        del attrs
        normalized = tag.lower()
        if normalized in _BOILERPLATE_TAGS:
            self._ignored_depth += 1
        if normalized == "title" and self._ignored_depth == 0:
            self._in_title = True
        if normalized in _BLOCK_TAGS and self._ignored_depth == 0:
            self.fragments.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Close ignored regions and add block boundaries."""

        normalized = tag.lower()
        if normalized == "title":
            self._in_title = False
        if normalized in _BOILERPLATE_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
        elif normalized in _BLOCK_TAGS and self._ignored_depth == 0:
            self.fragments.append("\n")

    def handle_data(self, data: str) -> None:
        """Collect visible text only."""

        if self._ignored_depth:
            return
        if self._in_title:
            self.title_fragments.append(data)
        else:
            self.fragments.append(data)

    def result(self) -> tuple[str | None, str]:
        """Return normalized title and content text."""

        title = _normalize_inline(" ".join(self.title_fragments))[:512] or None
        lines = (_normalize_inline(line) for line in "".join(self.fragments).splitlines())
        text = "\n".join(line for line in lines if line)
        return title, text


class HttpWebsiteFetcher(WebsiteFetcher):
    """Retrieve allowlisted public HTTPS pages through bounded HTTP streaming."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_response_bytes: int,
        user_agent: str,
        allowed_hosts: frozenset[str],
        require_public_ip: bool,
        transport: httpx.AsyncBaseTransport | None = None,
        resolver: HostResolver | None = None,
        network_backend: httpcore.AsyncNetworkBackend | None = None,
        max_redirects: int = 5,
    ) -> None:
        self._timeout = httpx.Timeout(timeout_seconds)
        self._max_response_bytes = max_response_bytes
        self._user_agent = user_agent
        self._allowed_hosts = allowed_hosts
        self._require_public_ip = require_public_ip
        self._transport = transport
        self._resolver = resolver or _resolve_host
        self._network_backend = network_backend
        self._max_redirects = max_redirects
        self._client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        """Create the HTTP client without performing a request."""

        if self._client is None:
            transport = self._transport
            if transport is None and self._require_public_ip:
                transport = build_pinned_transport(self._network_backend)
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=False,
                transport=transport,
                headers={"User-Agent": self._user_agent},
            )

    async def fetch(self, url: str, *, max_characters: int) -> WebsiteDocument:
        """Validate destination, retrieve bounded bytes, and extract clean text."""

        if self._client is None:
            raise ExternalDataError(ExternalErrorCategory.UNAVAILABLE, retryable=True)
        current_url = url
        for _ in range(self._max_redirects + 1):
            host = (urlsplit(current_url).hostname or "").lower().rstrip(".")
            addresses = await self._validate_destination(host)
            token = _PINNED_ADDRESSES.set({host: addresses[0]} if addresses else None)
            try:
                async with self._client.stream("GET", current_url) as response:
                    if response.status_code in _REDIRECT_STATUSES:
                        current_url = self._redirect_target(current_url, response)
                        continue
                    self._validate_status(response.status_code)
                    content_type = (
                        response.headers.get("content-type", "").split(";", 1)[0].lower()
                    )
                    if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
                        raise ExternalDataError(
                            ExternalErrorCategory.INVALID_RESPONSE,
                            retryable=False,
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > self._max_response_bytes:
                            raise ExternalDataError(
                                ExternalErrorCategory.INVALID_RESPONSE,
                                retryable=False,
                            )
                    break
            except httpx.TimeoutException as error:
                raise ExternalDataError(ExternalErrorCategory.TIMEOUT, retryable=True) from error
            except httpx.RequestError as error:
                raise ExternalDataError(ExternalErrorCategory.NETWORK, retryable=True) from error
            finally:
                _PINNED_ADDRESSES.reset(token)
        else:
            # Redirect chain exceeded the hop limit.
            raise ExternalDataError(ExternalErrorCategory.INVALID_RESPONSE, retryable=False)
        url = current_url

        text_value = bytes(body).decode(response.encoding or "utf-8", errors="replace")
        if content_type == "text/plain":
            title = None
            clean_text = _normalize_text(text_value)
        else:
            parser = _CleanTextParser()
            parser.feed(text_value)
            parser.close()
            title, clean_text = parser.result()
        truncated = len(clean_text) > max_characters
        clean_text = clean_text[:max_characters].rstrip()
        return WebsiteDocument(
            url=url,
            title=title,
            text=clean_text,
            content_type=content_type,
            word_count=len(clean_text.split()),
            fetched_at=datetime.now(UTC),
            truncated=truncated,
        )

    async def close(self) -> None:
        """Close the HTTP client idempotently."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _validate_destination(self, host: str) -> tuple[str, ...]:
        if not host or host == "localhost" or host.endswith(".local"):
            raise ExternalDataError(ExternalErrorCategory.INVALID_INPUT, retryable=False)
        if self._allowed_hosts and host not in self._allowed_hosts:
            raise ExternalDataError(ExternalErrorCategory.INVALID_INPUT, retryable=False)
        if not self._require_public_ip:
            return ()
        try:
            addresses = await self._resolver(host)
        except OSError as error:
            raise ExternalDataError(ExternalErrorCategory.NETWORK, retryable=True) from error
        if not addresses or any(not _is_public_address(value) for value in addresses):
            raise ExternalDataError(ExternalErrorCategory.INVALID_INPUT, retryable=False)
        return addresses

    @staticmethod
    def _redirect_target(current_url: str, response: httpx.Response) -> str:
        """Resolve and re-validate a redirect Location (HTTPS, no credentials, port 443)."""

        location = response.headers.get("location")
        if not location:
            raise ExternalDataError(ExternalErrorCategory.INVALID_RESPONSE, retryable=False)
        try:
            return normalize_https_url(urljoin(current_url, location))
        except ValueError as error:
            raise ExternalDataError(
                ExternalErrorCategory.INVALID_RESPONSE, retryable=False
            ) from error

    @staticmethod
    def _validate_status(status_code: int) -> None:
        if status_code == 404:
            raise ExternalDataError(ExternalErrorCategory.NOT_FOUND, retryable=False)
        if status_code in {401, 403}:
            raise ExternalDataError(ExternalErrorCategory.AUTHENTICATION, retryable=False)
        if status_code == 429:
            raise ExternalDataError(ExternalErrorCategory.RATE_LIMIT, retryable=True)
        if 300 <= status_code < 400:
            raise ExternalDataError(ExternalErrorCategory.INVALID_RESPONSE, retryable=False)
        if status_code >= 500:
            raise ExternalDataError(ExternalErrorCategory.UNAVAILABLE, retryable=True)
        if status_code >= 400:
            raise ExternalDataError(ExternalErrorCategory.INVALID_INPUT, retryable=False)


async def _resolve_host(host: str) -> tuple[str, ...]:
    """Resolve all destination addresses without blocking the event loop."""

    records = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
    return tuple(sorted({str(record[4][0]) for record in records}))


def _is_public_address(value: str) -> bool:
    address = ip_address(value)
    return address.is_global and not any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        )
    )


def _normalize_inline(value: str) -> str:
    return sub(r"\s+", " ", value).strip()


def _normalize_text(value: str) -> str:
    return "\n".join(
        normalized for line in value.splitlines() if (normalized := _normalize_inline(line))
    )
