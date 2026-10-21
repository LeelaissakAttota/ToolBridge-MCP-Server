"""Safe local HTTP client for the operational snapshot endpoint."""

import httpx

from toolbridge.operations.domain.models import OperationsSnapshot


class DashboardUnavailableError(RuntimeError):
    """Raised when the dashboard cannot obtain a valid safe snapshot."""


class DashboardClient:
    """Fetch operational data without sending mutations or credentials."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def fetch_snapshot(self) -> OperationsSnapshot:
        """Return a validated snapshot or one non-sensitive availability error."""

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                transport=self._transport,
            ) as client:
                response = client.get(
                    f"{self._base_url}/operations/snapshot",
                )
            response.raise_for_status()
            return OperationsSnapshot.model_validate_json(response.content)
        except (httpx.HTTPError, ValueError) as error:
            raise DashboardUnavailableError(
                "The ToolBridge monitoring API is unavailable or returned invalid data."
            ) from error
