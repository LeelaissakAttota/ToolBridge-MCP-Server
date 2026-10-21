"""Website Reader extraction, safety, failure, and lifecycle tests."""

import asyncio

import httpcore
import httpx
import pytest

from toolbridge.tools.adapters.website_reader import HttpWebsiteFetcher, PinnedNetworkBackend
from toolbridge.tools.application.website_reader import WebsiteReaderTool
from toolbridge.tools.domain.tool_errors import (
    ExternalDataError,
    WebsiteUnavailableError,
)
from toolbridge.tools.domain.website import WebsiteReaderInput


async def public_resolver(_: str) -> tuple[str, ...]:
    """Resolve a test host to a documentation-only public address."""

    return ("93.184.216.34",)


def build_fetcher(handler: httpx.MockTransport) -> HttpWebsiteFetcher:
    """Build a fully bounded website adapter for offline tests."""

    return HttpWebsiteFetcher(
        timeout_seconds=1,
        max_response_bytes=10_000,
        user_agent="ToolBridge-Tests",
        allowed_hosts=frozenset({"example.com"}),
        require_public_ip=True,
        transport=handler,
        resolver=public_resolver,
    )


def test_website_reader_extracts_clean_structured_content() -> None:
    html = """
    <html><head><title> Example Page </title><script>secret()</script></head>
    <body><header>Menu</header><main><h1>Heading</h1><p>Useful text.</p></main>
    <footer>Legal boilerplate</footer></body></html>
    """
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text=html,
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )
    )
    tool = WebsiteReaderTool(
        build_fetcher(transport),
        timeout_seconds=2,
        default_max_characters=1_000,
    )

    async def run() -> object:
        await tool.initialize()
        result = await tool.execute(WebsiteReaderInput(url="https://example.com/page#part"))
        await tool.close()
        return result

    result = asyncio.run(run())

    assert result.url == "https://example.com/page"
    assert result.title == "Example Page"
    assert "Heading" in result.text and "Useful text." in result.text
    assert "Menu" not in result.text
    assert "secret" not in result.text
    assert "Legal boilerplate" not in result.text
    assert result.word_count == 3


def test_website_reader_rejects_private_destinations_before_http() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, text="unused", request=request)

    async def private_resolver(_: str) -> tuple[str, ...]:
        return ("127.0.0.1",)

    fetcher = HttpWebsiteFetcher(
        timeout_seconds=1,
        max_response_bytes=1_024,
        user_agent="tests",
        allowed_hosts=frozenset(),
        require_public_ip=True,
        transport=httpx.MockTransport(handler),
        resolver=private_resolver,
    )
    tool = WebsiteReaderTool(fetcher, timeout_seconds=1, default_max_characters=100)

    async def run() -> None:
        await tool.initialize()
        with pytest.raises(WebsiteUnavailableError) as captured:
            await tool.execute(WebsiteReaderInput(url="https://private.test/"))
        await tool.close()
        assert captured.value.details == {"error_category": "invalid_input"}

    asyncio.run(run())
    assert calls == 0


def test_website_reader_normalizes_network_status_and_response_limits() -> None:
    responses = iter(
        (
            httpx.Response(503),
            httpx.Response(200, content=b"x" * 2_000, headers={"content-type": "text/plain"}),
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        response = next(responses)
        response.request = request
        return response

    fetcher = HttpWebsiteFetcher(
        timeout_seconds=1,
        max_response_bytes=1_024,
        user_agent="tests",
        allowed_hosts=frozenset({"example.com"}),
        require_public_ip=True,
        transport=httpx.MockTransport(handler),
        resolver=public_resolver,
    )
    tool = WebsiteReaderTool(fetcher, timeout_seconds=1, default_max_characters=100)

    async def run() -> None:
        await tool.initialize()
        with pytest.raises(WebsiteUnavailableError, match="website") as unavailable:
            await tool.execute(WebsiteReaderInput(url="https://example.com/first"))
        assert unavailable.value.retryable is True
        with pytest.raises(WebsiteUnavailableError) as oversized:
            await tool.execute(WebsiteReaderInput(url="https://example.com/second"))
        assert oversized.value.details == {"error_category": "invalid_response"}
        await tool.close()

    asyncio.run(run())


class _RecordingBackend(httpcore.AsyncNetworkBackend):
    """Fake network backend that records TCP destinations and refuses to connect."""

    def __init__(self) -> None:
        self.destinations: list[tuple[str, int]] = []

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.destinations.append((host, port))
        raise httpcore.ConnectError("recorded")

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


def test_website_reader_connects_to_validated_ip_not_a_fresh_lookup() -> None:
    backend = _RecordingBackend()
    fetcher = HttpWebsiteFetcher(
        timeout_seconds=1,
        max_response_bytes=10_000,
        user_agent="ToolBridge-Tests",
        allowed_hosts=frozenset(),
        require_public_ip=True,
        resolver=public_resolver,
        network_backend=backend,
    )

    async def run() -> None:
        await fetcher.initialize()
        try:
            await fetcher.fetch("https://rebind.example.com/", max_characters=100)
        finally:
            await fetcher.close()

    with pytest.raises(ExternalDataError):
        asyncio.run(run())
    # TCP goes to the validated address; the hostname (SNI/Host) is never re-resolved.
    assert backend.destinations == [("93.184.216.34", 443)]


def test_pinned_backend_refuses_unvalidated_hosts() -> None:
    backend = _RecordingBackend()
    pinned = PinnedNetworkBackend(backend)

    with pytest.raises(httpcore.ConnectError):
        asyncio.run(pinned.connect_tcp("internal.example", 443))
    assert backend.destinations == []


def _redirecting_fetcher(routes: dict[str, httpx.Response], resolver=public_resolver, **kw):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return routes[str(request.url)]

    fetcher = HttpWebsiteFetcher(
        timeout_seconds=1,
        max_response_bytes=10_000,
        user_agent="ToolBridge-Tests",
        allowed_hosts=frozenset(),
        require_public_ip=True,
        transport=httpx.MockTransport(handler),
        resolver=resolver,
        **kw,
    )
    return fetcher, seen


def _run_fetch(fetcher: HttpWebsiteFetcher, url: str) -> object:
    async def run() -> object:
        await fetcher.initialize()
        try:
            return await fetcher.fetch(url, max_characters=1_000)
        finally:
            await fetcher.close()

    return asyncio.run(run())


def _html(text: str) -> httpx.Response:
    return httpx.Response(200, text=f"<p>{text}</p>", headers={"content-type": "text/html"})


def test_website_reader_follows_safe_redirects_and_reports_final_url() -> None:
    fetcher, seen = _redirecting_fetcher(
        {
            "https://a.example/": httpx.Response(
                301, headers={"location": "https://www.a.example/x"}
            ),
            "https://www.a.example/x": httpx.Response(302, headers={"location": "/final"}),
            "https://www.a.example/final": _html("Done"),
        }
    )

    result = _run_fetch(fetcher, "https://a.example/")

    assert result.text == "Done"
    assert result.url == "https://www.a.example/final"
    assert seen == ["https://a.example/", "https://www.a.example/x", "https://www.a.example/final"]


@pytest.mark.parametrize(
    "location",
    ["http://a.example/insecure", "https://user:pw@a.example/", "https://a.example:8443/"],
)
def test_website_reader_rejects_unsafe_redirect_targets(location: str) -> None:
    fetcher, seen = _redirecting_fetcher(
        {"https://a.example/": httpx.Response(302, headers={"location": location})}
    )

    with pytest.raises(ExternalDataError):
        _run_fetch(fetcher, "https://a.example/")
    assert seen == ["https://a.example/"]


def test_website_reader_revalidates_redirect_destination_ip() -> None:
    async def resolver(host: str) -> tuple[str, ...]:
        return ("10.0.0.5",) if host == "internal.example" else ("93.184.216.34",)

    fetcher, seen = _redirecting_fetcher(
        {
            "https://a.example/": httpx.Response(
                302, headers={"location": "https://internal.example/admin"}
            )
        },
        resolver=resolver,
    )

    with pytest.raises(ExternalDataError):
        _run_fetch(fetcher, "https://a.example/")
    assert seen == ["https://a.example/"]


def test_website_reader_caps_redirect_hops() -> None:
    fetcher, seen = _redirecting_fetcher(
        {"https://a.example/": httpx.Response(302, headers={"location": "https://a.example/"})},
        max_redirects=3,
    )

    with pytest.raises(ExternalDataError):
        _run_fetch(fetcher, "https://a.example/")
    assert len(seen) == 4
