"""Managed Website Reader Tool using a replaceable retrieval adapter."""

from datetime import UTC, datetime

from toolbridge.core.contracts import ToolDefinition
from toolbridge.tools.application.phase5_ports import WebsiteFetcher
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.models import ToolHealthState, ToolHealthStatus
from toolbridge.tools.domain.tool_errors import ExternalDataError, WebsiteUnavailableError
from toolbridge.tools.domain.website import WebsiteReaderInput, WebsiteReaderOutput


class WebsiteReaderTool(BaseTool):
    """Read one validated public web page and return clean structured text."""

    def __init__(
        self,
        fetcher: WebsiteFetcher,
        *,
        timeout_seconds: float,
        default_max_characters: int,
    ) -> None:
        self._fetcher = fetcher
        self._default_max_characters = default_max_characters
        self._definition = ToolDefinition(
            name="website_reader",
            description="Read a public HTTPS web page and return clean structured text.",
            input_model=WebsiteReaderInput,
            output_model=WebsiteReaderOutput,
            handler=self.execute,
            timeout_seconds=timeout_seconds,
        )
        self._state = ToolHealthState.UNINITIALIZED
        self._last_success_at: datetime | None = None
        self._last_failure_at: datetime | None = None

    @property
    def definition(self) -> ToolDefinition:
        """Return the immutable Website Reader registration contract."""

        return self._definition

    async def initialize(self) -> None:
        """Initialize the website adapter without outbound traffic."""

        await self._fetcher.initialize()
        self._state = ToolHealthState.HEALTHY

    async def execute(self, arguments: WebsiteReaderInput) -> WebsiteReaderOutput:
        """Retrieve and clean a validated page."""

        maximum = min(
            arguments.max_characters or self._default_max_characters,
            self._default_max_characters,
        )
        try:
            result = await self._fetcher.fetch(arguments.url, max_characters=maximum)
        except ExternalDataError as error:
            self._last_failure_at = datetime.now(UTC)
            raise WebsiteUnavailableError(error.category) from error
        self._last_success_at = datetime.now(UTC)
        return result

    async def health_check(self) -> ToolHealthStatus:
        """Return local adapter lifecycle health without network access."""

        return ToolHealthStatus(
            tool_name=self._definition.name,
            status=self._state,
            checked_at=datetime.now(UTC),
            last_success_at=self._last_success_at,
            last_failure_at=self._last_failure_at,
        )

    async def close(self) -> None:
        """Close the website adapter and mark the tool closed."""

        await self._fetcher.close()
        self._state = ToolHealthState.CLOSED
