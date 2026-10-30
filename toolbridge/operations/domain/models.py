"""Safe, immutable models exposed by the operational monitoring API."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from toolbridge.providers.domain.routing import ModelRoutingRecord


class LifecycleState(StrEnum):
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class SafeLogLevel(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ReadinessCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    name: str
    ready: bool
    status: str


class ReadinessSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    status: str
    ready: bool
    checked_at: datetime
    checks: tuple[ReadinessCheck, ...]


class SystemOverview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: str
    uptime_seconds: float = Field(ge=0)
    environment: str
    current_phase: str
    health_status: str
    lifecycle: LifecycleState
    started_at: datetime


class ProviderMonitor(BaseModel):
    """Safe provider health, routing, discovery, usage, and budget summary."""

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
    errors: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    success_rate: float = Field(default=1.0, ge=0, le=1)
    health_score: float = Field(default=1.0, ge=0, le=1)
    available: bool = False
    capabilities: tuple[str, ...] = ()
    model_count: int = Field(default=0, ge=0)
    active_model: str | None = None
    selection_reason: str | None = None
    model_cache_age_seconds: float | None = Field(default=None, ge=0)
    model_discovery_time_ms: float | None = Field(default=None, ge=0)
    daily_budget_usd: float | None = Field(default=None, ge=0)
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    per_request_budget_usd: float | None = Field(default=None, ge=0)
    daily_cost_usd: float = Field(default=0.0, ge=0)
    monthly_cost_usd: float = Field(default=0.0, ge=0)
    soft_limit_reached: bool = False
    hard_limit_reached: bool = False
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)


class ProviderModelMonitor(BaseModel):
    """Safe discovered-model metadata for provider operations."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    provider: str
    model: str
    capabilities: tuple[str, ...]
    available: bool
    is_free: bool
    context_window: int | None = Field(default=None, ge=1)
    input_cost_per_million_tokens_usd: float = Field(ge=0)
    output_cost_per_million_tokens_usd: float = Field(ge=0)
    latency_ms: float | None = Field(default=None, ge=0)
    health_score: float = Field(ge=0, le=1)
    reasoning_quality: float = Field(ge=0, le=1)
    discovered_at: datetime | None = None


class ToolMonitor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    tool_name: str
    display_name: str
    registered: bool
    health: str
    execution_count: int = Field(ge=0)
    average_response_time_ms: float = Field(ge=0)
    last_execution: datetime | None = None


class MetricsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    total_requests: int = Field(ge=0)
    successful_requests: int = Field(ge=0)
    failed_requests: int = Field(ge=0)
    error_categories: dict[str, int]
    average_response_time_ms: float = Field(ge=0)
    provider_usage: dict[str, int]
    tool_usage: dict[str, int]


class CostSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    estimated_token_usage: int = Field(ge=0)
    estimated_api_cost_usd: float = Field(ge=0)
    requests_per_provider: dict[str, int]
    cost_per_provider: dict[str, float]


class SafeLogEntry(BaseModel):
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
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    system: SystemOverview
    readiness: ReadinessSnapshot
    providers: tuple[ProviderMonitor, ...]
    models: tuple[ProviderModelMonitor, ...] = ()
    tools: tuple[ToolMonitor, ...]
    metrics: MetricsSummary
    costs: CostSummary
    logs: tuple[SafeLogEntry, ...]
    routing: tuple[ModelRoutingRecord, ...] = ()
