"""Synchronous ASGI test client built on httpx.ASGITransport.

Replaces ``fastapi.testclient.TestClient``, whose httpx backend is deprecated in
Starlette. It runs the application's lifespan and every request on one anyio
blocking portal, so streaming MCP session managers start and stop correctly.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, ExitStack
from typing import Any

import httpx
from anyio.from_thread import start_blocking_portal
from starlette.types import ASGIApp


class ASGITestClient(AbstractContextManager["ASGITestClient"]):
    """Minimal sync client: ``with ASGITestClient(app) as client: client.get(...)``."""

    __test__ = False  # not a pytest test class

    def __init__(
        self,
        app: ASGIApp,
        *,
        base_url: str = "http://127.0.0.1:8000",
        lifespan_app: Any | None = None,
    ) -> None:
        self._app = app
        self._base_url = base_url
        # The app that owns the lifespan (defaults to ``app``; differs when wrapped).
        self._lifespan_app = lifespan_app if lifespan_app is not None else app
        self._stack = ExitStack()
        self._portal: Any = None
        self._client: httpx.AsyncClient | None = None

    def __enter__(self) -> ASGITestClient:
        self._portal = self._stack.enter_context(start_blocking_portal())
        router = getattr(self._lifespan_app, "router", None)
        if router is not None and getattr(router, "lifespan_context", None) is not None:
            self._stack.enter_context(
                self._portal.wrap_async_context_manager(
                    router.lifespan_context(self._lifespan_app)
                )
            )
        self._client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self._app),
            base_url=self._base_url,
        )
        self._stack.callback(lambda: self._portal.call(self._client.aclose))
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stack.__exit__(*exc_info)  # type: ignore[arg-type]

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        if self._client is None:
            raise RuntimeError("ASGITestClient must be used as a context manager")
        return self._portal.call(lambda: self._client.request(method, url, **kwargs))

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)
