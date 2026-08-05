"""Safe, normalized errors for provider operations."""

from toolbridge.providers.domain.models import ProviderErrorCategory, ProviderName

_SAFE_MESSAGES = {
    ProviderErrorCategory.TIMEOUT: "The provider request timed out.",
    ProviderErrorCategory.AUTHENTICATION: "The provider rejected its credentials.",
    ProviderErrorCategory.RATE_LIMIT: "The provider rate limit was reached.",
    ProviderErrorCategory.UNAVAILABLE: "The provider is unavailable.",
    ProviderErrorCategory.INVALID_REQUEST: "The provider request is invalid.",
    ProviderErrorCategory.INVALID_RESPONSE: "The provider returned an invalid response.",
    ProviderErrorCategory.INTERNAL: "The provider request failed internally.",
}
_RETRYABLE = {
    ProviderErrorCategory.TIMEOUT,
    ProviderErrorCategory.RATE_LIMIT,
    ProviderErrorCategory.UNAVAILABLE,
}
_FAILOVER_ELIGIBLE = _RETRYABLE | {
    ProviderErrorCategory.AUTHENTICATION,
    ProviderErrorCategory.INVALID_RESPONSE,
    ProviderErrorCategory.INTERNAL,
}


class ProviderError(Exception):
    """Normalized provider error that never contains a vendor response body."""

    def __init__(
        self,
        category: ProviderErrorCategory,
        provider: ProviderName | None,
        *,
        retry_after_seconds: float | None = None,
    ) -> None:
        message = _SAFE_MESSAGES[category]
        super().__init__(message)
        self.category = category
        self.provider = provider
        self.message = message
        self.retry_after_seconds = retry_after_seconds

    @property
    def retryable(self) -> bool:
        """Return whether another attempt against the same provider is safe."""

        return self.category in _RETRYABLE

    @property
    def failover_eligible(self) -> bool:
        """Return whether another configured provider may safely receive the request."""

        return self.category in _FAILOVER_ELIGIBLE


class ProviderRoutingError(ProviderError):
    """Raised when no configured provider can service a request."""

    def __init__(self) -> None:
        super().__init__(ProviderErrorCategory.UNAVAILABLE, provider=None)
