"""Website Reader extraction, safety, failure, and lifecycle tests."""

import asyncio

import httpx
import pytest

from toolbridge.tools.adapters.website_reader import HttpWebsiteFetcher
from toolbridge.tools.application.website_reader import WebsiteReaderTool
from toolbridge.tools.domain.tool_errors import WebsiteUnavailableError
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
