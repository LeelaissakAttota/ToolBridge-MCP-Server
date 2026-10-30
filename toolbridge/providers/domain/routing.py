"""Sanitized model-routing metadata.

Only routing facts are kept: provider, model, why it was chosen, and the failover
chain with stable error categories. Prompts, tool arguments, documents, and model
outputs are never part of these records.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RoutingMode(StrEnum):
    AUTO = "auto"
    FIXED = "fixed"


class RoutingOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ModelRoutingAttempt(BaseModel):
    """One model tried while serving a request."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: str | None = Field(default=None, max_length=64)
    model: str = Field(min_length=1, max_length=256)
    outcome: RoutingOutcome
    error_category: str | None = Field(default=None, max_length=64)
    reason: str | None = Field(default=None, max_length=300)


class ModelRoutingRecord(BaseModel):
    """Which provider/model served one LLM request, why, and any failover."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    timestamp: datetime
    request_id: str | None = Field(default=None, max_length=128)
    tool: str = Field(min_length=1, max_length=64)
    mode: RoutingMode
    status: RoutingOutcome
    selected_provider: str | None = Field(default=None, max_length=64)
    selected_model: str | None = Field(default=None, max_length=256)
    selection_reason: str | None = Field(default=None, max_length=300)
    failover: bool = False
    attempts: tuple[ModelRoutingAttempt, ...] = ()
    error_category: str | None = Field(default=None, max_length=64)

    def chain(self) -> str:
        """Human-readable failover chain, e.g. ``a (rate_limit) -> b``."""

        parts = []
        for item in self.attempts:
            label = item.model
            if item.outcome is RoutingOutcome.FAILED:
                label += f" ({item.error_category or 'failed'})"
            parts.append(label)
        return " -> ".join(parts)
