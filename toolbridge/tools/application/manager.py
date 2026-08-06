"""Registration, lifecycle, health, and metrics management for tools."""

import asyncio

from toolbridge.core.registry import ToolRegistry
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.models import ToolStatusSnapshot


class ToolManager:
    """Own managed tool registration and process lifecycle."""

    def __init__(
        self,
        tools: tuple[BaseTool, ...],
        metrics: InMemoryToolMetrics,
    ) -> None:
        self._tools = tools
        self._metrics = metrics
        self._initialized: list[BaseTool] = []

    @property
    def tools(self) -> tuple[BaseTool, ...]:
        """Return managed tools in configured registration order."""

        return self._tools

    def register_all(self, registry: ToolRegistry) -> None:
        """Automatically register every managed tool definition."""

        for tool in self._tools:
            registry.register(tool.definition)

    async def initialize(self) -> None:
        """Initialize tools in order and roll back partial startup on failure."""

        if self._initialized:
            return
        try:
            for tool in self._tools:
                await tool.initialize()
                self._initialized.append(tool)
        except BaseException:
            await self.close()
            raise

    async def statuses(self) -> tuple[ToolStatusSnapshot, ...]:
        """Probe every tool concurrently and combine health with metrics."""

        health_values = await asyncio.gather(
            *(tool.health_check() for tool in self._tools)
        )
        return tuple(
            ToolStatusSnapshot(
                health=health,
                metrics=self._metrics.snapshot(health.tool_name),
            )
            for health in health_values
        )

    async def close(self) -> None:
        """Close initialized tools in reverse order, attempting every close."""

        failures: list[Exception] = []
        for tool in reversed(self._initialized):
            try:
                await tool.close()
            except Exception as error:
                failures.append(error)
        self._initialized.clear()
        if failures:
            raise ExceptionGroup("one or more tools failed to close", failures)
