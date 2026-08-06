"""Normalized internal and client-facing errors for Phase 5 tools."""

from enum import StrEnum

from toolbridge.core.contracts import ErrorCode
from toolbridge.core.errors import ToolBridgeError


class ExternalErrorCategory(StrEnum):
    """Normalized failures shared by read-only external data adapters."""

    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    UNAVAILABLE = "unavailable"
    INVALID_RESPONSE = "invalid_response"


class ExternalDataError(Exception):
    """Internal provider error that excludes URLs, payloads, and secrets."""

    def __init__(self, category: ExternalErrorCategory, *, retryable: bool) -> None:
        super().__init__(f"external data request failed: {category.value}")
        self.category = category
        self.retryable = retryable


class WebsiteUnavailableError(ToolBridgeError):
    """Safe website failure returned after bounded retrieval."""

    def __init__(self, category: ExternalErrorCategory) -> None:
        super().__init__(
            ErrorCode.WEBSITE_UNAVAILABLE,
            "The website could not be read safely.",
            retryable=category in _RETRYABLE_EXTERNAL,
            details={"error_category": category.value},
        )


class DatabaseQueryFailedError(ToolBridgeError):
    """Safe database failure without query or connection details."""

    def __init__(self, *, timed_out: bool = False) -> None:
        super().__init__(
            ErrorCode.DATABASE_QUERY_FAILED,
            "The read-only database query could not be completed.",
            retryable=timed_out,
            details={"error_category": "timeout" if timed_out else "database"},
        )


class FileAnalysisFailedError(ToolBridgeError):
    """Safe CSV failure without filesystem details."""

    def __init__(self, category: str) -> None:
        super().__init__(
            ErrorCode.FILE_ANALYSIS_FAILED,
            "The CSV file could not be analyzed safely.",
            details={"error_category": category},
        )


class CurrencyRateUnavailableError(ToolBridgeError):
    """Safe currency-provider failure after bounded retries."""

    def __init__(self, category: ExternalErrorCategory) -> None:
        super().__init__(
            ErrorCode.CURRENCY_RATE_UNAVAILABLE,
            "Currency exchange rates are temporarily unavailable.",
            retryable=category in _RETRYABLE_EXTERNAL,
            details={"error_category": category.value},
        )


class LLMAnalysisUnavailableError(ToolBridgeError):
    """Safe LLM routing failure without prompt or provider payload details."""

    def __init__(self, category: str) -> None:
        super().__init__(
            ErrorCode.LLM_ANALYSIS_UNAVAILABLE,
            "The text analysis service is temporarily unavailable.",
            retryable=category in {"timeout", "rate_limit", "unavailable"},
            details={"error_category": category},
        )


_RETRYABLE_EXTERNAL = {
    ExternalErrorCategory.TIMEOUT,
    ExternalErrorCategory.NETWORK,
    ExternalErrorCategory.RATE_LIMIT,
    ExternalErrorCategory.UNAVAILABLE,
}
