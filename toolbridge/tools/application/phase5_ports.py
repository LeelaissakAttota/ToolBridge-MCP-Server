"""Replaceable ports used by the Phase 5 application services."""

from abc import ABC, abstractmethod

from toolbridge.tools.domain.csv_analysis import CSVAnalysisOutput
from toolbridge.tools.domain.currency import CurrencyProviderName, CurrencyRateSet
from toolbridge.tools.domain.sql_query import SQLQueryOutput, SqlValue
from toolbridge.tools.domain.website import WebsiteDocument


class WebsiteFetcher(ABC):
    """Adapter boundary for validated public website retrieval."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize network resources."""

    @abstractmethod
    async def fetch(self, url: str, *, max_characters: int) -> WebsiteDocument:
        """Return cleaned structured content or a normalized adapter error."""

    @abstractmethod
    async def close(self) -> None:
        """Release network resources."""


class ReadOnlyQueryExecutor(ABC):
    """Database-neutral port ready for SQLite and future PostgreSQL adapters."""

    @abstractmethod
    async def execute(
        self,
        query: str,
        parameters: dict[str, SqlValue],
        *,
        max_rows: int,
    ) -> SQLQueryOutput:
        """Execute one validated read-only query with bounded output."""


class CSVDataSource(ABC):
    """Replaceable port for bounded CSV file analysis."""

    @abstractmethod
    async def analyze(
        self,
        relative_path: str,
        *,
        preview_rows: int,
    ) -> CSVAnalysisOutput:
        """Analyze a file beneath the configured root."""


class ExchangeRateProvider(ABC):
    """Provider-neutral interface for base-unit exchange rates."""

    @property
    @abstractmethod
    def name(self) -> CurrencyProviderName:
        """Return the stable provider identifier."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider resources."""

    @abstractmethod
    async def get_rates(
        self,
        base_currency: str,
        target_currencies: tuple[str, ...],
    ) -> CurrencyRateSet:
        """Return normalized base-unit rates."""

    @abstractmethod
    async def close(self) -> None:
        """Release provider resources."""
