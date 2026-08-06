"""Provider-neutral contracts for safe website reading."""

from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, field_validator

from toolbridge.core.contracts import ToolInput, ToolOutput


class WebsiteReaderInput(ToolInput):
    """Validated public web page request."""

    url: str = Field(min_length=1, max_length=2_048)
    max_characters: int | None = Field(default=None, ge=1, le=500_000)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Require a credential-free HTTPS URL and remove its fragment."""

        normalized = value.strip()
        parsed = urlsplit(normalized)
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError("url must be a credential-free HTTPS URL")
        if parsed.port not in {None, 443}:
            raise ValueError("url must use the standard HTTPS port")
        return urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


class WebsiteDocument(ToolOutput):
    """Clean normalized content produced by a website adapter."""

    url: str = Field(min_length=1, max_length=2_048)
    title: str | None = Field(default=None, max_length=512)
    text: str = Field(max_length=500_000)
    content_type: str = Field(min_length=1, max_length=128)
    word_count: int = Field(ge=0)
    fetched_at: datetime
    truncated: bool

    @field_validator("fetched_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        """Require an offset-aware fetch timestamp."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must include a timezone")
        return value


WebsiteReaderOutput = WebsiteDocument
