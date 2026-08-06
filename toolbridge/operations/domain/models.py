"""Safe, immutable models exposed by the operational monitoring API."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LifecycleState(StrEnum):
    """Server process lifecycle states used by readiness checks."""

    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class SafeLogLevel(StrEnum):
    """Allowlisted log levels retained by the bounded viewer buffer."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ReadinessCheck(BaseModel):
    """One non-secret readiness decision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str
    ready: bool
    status: str


class ReadinessSnapshot(BaseModel):
    """Aggregate readiness state suitable for an HTTP response."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    status: str
    ready: bool
    checked_at: datetime
    checks: tuple[ReadinessCheck, ...]


class SystemOverview(BaseModel):
    """Read-only server identity and lifecycle information."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    version: str
    uptime_seconds: float = Field(ge=0)
    environment: str
    current_phase: str
    health_status: str
    lifecycle: LifecycleState
    started_at: datetime


class ProviderMonitor(BaseModel):
    """Safe provider status, timing, usage, and cost summary."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    provider: str
    configured: bool
    priority: int
    status: str
    active: bool
    failover_active: bool
    response_latency_ms: float | None = Field(default=None, ge=0)
    last_successful_request: datetime | None = None
    last_failed_request: datetime | None = None
    error_category: str | None = None
    requests: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)


class ToolMonitor(BaseModel):
    """Registration, health, and execution metrics for one MCP tool."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    tool_name: str
    display_name: str
    registered: bool
    health: str
    execution_count: int = Field(ge=0)
    average_response_time_ms: float = Field(ge=0)
    last_execution: datetime | None = None


class MetricsSummary(BaseModel):
    """Aggregate request, error, provider, and tool metrics."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    total_requests: int = Field(ge=0)
    successful_requests: int = Field(ge=0)
    failed_requests: int = Field(ge=0)
    error_categories: dict[str, int]
    average_response_time_ms: float = Field(ge=0)
    provider_usage: dict[str, int]
    tool_usage: dict[str, int]


class CostSummary(BaseModel):
    """Configuration-driven provider token and API-cost estimates."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    estimated_token_usage: int = Field(ge=0)
    estimated_api_cost_usd: float = Field(ge=0)
    requests_per_provider: dict[str, int]
    cost_per_provider: dict[str, float]


class SafeLogEntry(BaseModel):
    """Allowlisted event metadata retained for dashboard display."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    timestamp: datetime
    level: SafeLogLevel
    source: str
    event: str
    component: str | None = None
    status: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    request_id: str | None = None
    error_category: str | None = None


class OperationsSnapshot(BaseModel):
    """Complete safe dashboard payload returned by the operational API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    system: SystemOverview
    readiness: ReadinessSnapshot
    providers: tuple[ProviderMonitor, ...]
    tools: tuple[ToolMonitor, ...]
    metrics: MetricsSummary
    costs: CostSummary
    logs: tuple[SafeLogEntry, ...]
