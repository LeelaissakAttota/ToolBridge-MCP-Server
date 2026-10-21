"""Provider-neutral contracts for LLM text analysis."""

from enum import StrEnum

from pydantic import Field

from toolbridge.core.contracts import ToolInput, ToolOutput
from toolbridge.providers.domain.models import ProviderName


class AnalysisOperation(StrEnum):
    """Supported deterministic request modes for LLM analysis."""

    ANALYZE = "analyze"
    SUMMARIZE = "summarize"


class LLMAnalysisInput(ToolInput):
    """Validated text analysis request."""

    operation: AnalysisOperation
    text: str = Field(min_length=1, max_length=131_072)
    instructions: str | None = Field(default=None, min_length=1, max_length=2_000)


class LLMAnalysisOutput(ToolOutput):
    """Structured provider-neutral analysis response."""

    operation: AnalysisOperation
    content: str = Field(max_length=1_000_000)
    provider: ProviderName | str
    model: str = Field(min_length=1, max_length=256)
    request_id: str = Field(min_length=1, max_length=128)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
