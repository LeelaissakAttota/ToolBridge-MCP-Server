"""Tests for readiness, provider monitoring, and tool monitoring snapshots."""

import asyncio

from toolbridge.bootstrap import build_core_runtime
from toolbridge.config import Settings
from toolbridge.core.ports import NullExecutionEventLogger


def test_operations_snapshot_is_read_only_complete_and_network_free() -> None:
    settings = Settings(_env_file=None)
    runtime = build_core_runtime(settings, NullExecutionEventLogger())

    async def run() -> object:
        runtime.operations.validate_startup()
        await runtime.tool_manager.initialize()
        await runtime.provider_router.initialize()
        runtime.operations.mark_ready()
        snapshot = runtime.operations.snapshot()
        runtime.operations.mark_stopping()
        await runtime.provider_router.close()
        await runtime.tool_manager.close()
        runtime.operations.mark_stopped()
        return snapshot

    snapshot = asyncio.run(run())

    assert snapshot.readiness.ready is True
    assert snapshot.system.version == "0.6.0"
    assert snapshot.system.current_phase.startswith("Phase 6")
    assert len(snapshot.tools) == 7
    assert all(item.registered for item in snapshot.tools)
    assert [item.provider for item in snapshot.providers] == [
        "cerebras",
        "nvidia",
        "openrouter",
    ]
    assert all(not item.configured for item in snapshot.providers)
    assert snapshot.metrics.total_requests == 0


def test_readiness_is_false_before_and_after_managed_lifecycle() -> None:
    runtime = build_core_runtime(
        Settings(_env_file=None),
        NullExecutionEventLogger(),
    )

    assert runtime.operations.readiness().ready is False

    runtime.operations.mark_stopped()

    assert runtime.operations.readiness().ready is False

