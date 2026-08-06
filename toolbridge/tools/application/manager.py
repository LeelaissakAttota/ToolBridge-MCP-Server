"""Registration, lifecycle, health, and metrics management for tools."""

import asyncio
from datetime import UTC, datetime

from toolbridge.core.registry import ToolRegistry
from toolbridge.tools.application.metrics import InMemoryToolMetrics
from toolbridge.tools.application.ports import BaseTool
from toolbridge.tools.domain.models import (
    ToolHealthState,
    ToolHealthStatus,
    ToolStatusSnapshot,
)


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
        self._health_cache: dict[str, ToolHealthStatus] = {}

    @property
    def tools(self) -> tuple[BaseTool, ...]:
        """Return managed tools in configured registration order."""

        return self._tools

    @property
    def is_initialized(self) -> bool:
        """Return whether every configured tool completed initialization."""

        return len(self._initialized) == len(self._tools)

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
                self._health_cache[tool.definition.name] = ToolHealthStatus(
                    tool_name=tool.definition.name,
                    status=ToolHealthState.HEALTHY,
                    checked_at=datetime.now(UTC),
                    last_success_at=datetime.now(UTC),
                )
        except BaseException:
            await self.close()
            raise

    async def statuses(self) -> tuple[ToolStatusSnapshot, ...]:
        """Probe every tool concurrently and combine health with metrics."""

        health_values = await asyncio.gather(*(tool.health_check() for tool in self._tools))
        self._health_cache.update((health.tool_name, health) for health in health_values)
        return tuple(
            ToolStatusSnapshot(
                health=health,
                metrics=self._metrics.snapshot(health.tool_name),
            )
            for health in health_values
        )

    def monitoring_statuses(self) -> tuple[ToolStatusSnapshot, ...]:
        """Return cached lifecycle health without external I/O or side effects."""

        checked_at = datetime.now(UTC)
        values: list[ToolStatusSnapshot] = []
        for tool in self._tools:
            name = tool.definition.name
            health = self._health_cache.get(
                name,
                ToolHealthStatus(
                    tool_name=name,
                    status=ToolHealthState.UNINITIALIZED,
                    checked_at=checked_at,
                ),
            )
            values.append(
                ToolStatusSnapshot(
                    health=health,
                    metrics=self._metrics.snapshot(name),
                )
            )
        return tuple(values)

    async def close(self) -> None:
        """Close initialized tools in reverse order, attempting every close."""

        failures: list[Exception] = []
        for tool in reversed(self._initialized):
            try:
                await tool.close()
            except Exception as error:
                failures.append(error)
            finally:
                self._health_cache[tool.definition.name] = ToolHealthStatus(
                    tool_name=tool.definition.name,
                    status=ToolHealthState.CLOSED,
                    checked_at=datetime.now(UTC),
                )
        self._initialized.clear()
        if failures:
            raise ExceptionGroup("one or more tools failed to close", failures)
