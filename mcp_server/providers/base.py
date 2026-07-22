"""Base interface for provider implementations.

Providers are external services (e.g., AI models, databases) that the
server interacts with. Concrete providers should subclass ``ProviderBase``
and implement the abstract ``connect`` and ``close`` methods.
"""

from abc import ABC, abstractmethod

class ProviderBase(ABC):
    """Abstract base class for all providers.

    Subclasses must implement ``connect`` and ``close``. Additional methods
    can be defined as needed by each concrete provider.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish a connection to the underlying service."""

    @abstractmethod
    def close(self) -> None:
        """Close any open resources or connections."""
