"""Base interface for LLM provider implementations.

This module defines the abstract ProviderBase class that all LLM providers
must implement. It provides a unified interface for text generation,
streaming, health checks, and model management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    api_key: str = ""
    base_url: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    default_model: Optional[str] = None
    extra_headers: dict = field(default_factory=dict)
    extra_params: dict = field(default_factory=dict)


@dataclass
class GenerationRequest:
    """Request for text generation."""
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    stop: Optional[list[str]] = None
    stream: bool = False
    extra_params: dict = field(default_factory=dict)


@dataclass
class GenerationResponse:
    """Response from text generation."""
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0
    finish_reason: Optional[str] = None
    latency_ms: float = 0.0
    provider: str = ""


@dataclass
class TokenUsage:
    """Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    healthy: bool
    latency_ms: float = 0.0
    available_models: list[str] = field(default_factory=list)
    last_check: float = field(default_factory=time.time)
    error: Optional[str] = None


@dataclass
class ModelInfo:
    """Information about a model."""
    name: str
    max_tokens: int
    cost_per_1k_prompt: float = 0.0
    cost_per_1k_completion: float = 0.0
    supports_streaming: bool = True
    supports_tools: bool = False
    context_window: int = 4096


class ProviderBase(ABC):
    """Abstract base class for all LLM providers.

    All providers must implement the following methods:
    - generate(): Synchronous text generation
    - stream(): Streaming text generation
    - health_check(): Check provider availability
    - available_models(): List available models
    - count_tokens(): Count tokens in text
    - estimate_cost(): Estimate request cost
    """

    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration.

        Args:
            config: Provider configuration including API key, timeouts, etc.
        """
        self.config = config
        self._client: Any = None
        self._initialized = False
        self._token_usage = TokenUsage()
        self._cost_estimate = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'cerebras', 'nvidia', 'openrouter')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Return the default model name for this provider."""
        pass

    @abstractmethod
    async def _initialize_client(self) -> None:
        """Initialize the provider's client (async)."""
        pass

    def _ensure_initialized(self) -> None:
        """Ensure client is initialized."""
        if not self._initialized:
            raise RuntimeError(f"Provider {self.name} not initialized. Call initialize() first.")

    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self._initialized:
            await self._initialize_client()
            self._initialized = True
            logger.info(f"Provider {self.name} initialized")

    async def close(self) -> None:
        """Close the provider and release resources."""
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()
        self._initialized = False
        logger.info(f"Provider {self.name} closed")

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text synchronously.

        Args:
            request: Generation request with prompt and parameters.

        Returns:
            GenerationResponse with generated text and metadata.
        """
        pass

    @abstractmethod
    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        """Stream text generation.

        Args:
            request: Generation request with prompt and parameters.

        Yields:
            Text chunks as they are generated.
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """Check provider health.

        Returns:
            HealthCheckResult with status, latency, and available models.
        """
        pass

    @abstractmethod
    async def available_models(self) -> list[ModelInfo]:
        """Get list of available models.

        Returns:
            List of ModelInfo with model details.
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for.
            model: Optional model name (uses default if not provided).

        Returns:
            Number of tokens.
        """
        pass

    @abstractmethod
    async def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate cost for a generation request.

        Args:
            request: Generation request to estimate cost for.

        Returns:
            Estimated cost in USD.
        """
        pass

    def get_token_usage(self) -> TokenUsage:
        """Get current token usage.

        Returns:
            TokenUsage with prompt, completion, and total tokens.
        """
        return self._token_usage

    def reset_token_usage(self) -> None:
        """Reset token usage counters."""
        self._token_usage = TokenUsage()

    def get_cost_estimate(self) -> float:
        """Get current cost estimate.

        Returns:
            Estimated cost in USD.
        """
        return self._cost_estimate

    def reset_cost_estimate(self) -> None:
        """Reset cost estimate."""
        self._cost_estimate = 0.0

    def _update_token_usage(self, prompt_tokens: int, completion_tokens: int, cost: float = 0.0) -> None:
        """Update token usage and cost tracking."""
        self._token_usage.prompt_tokens += prompt_tokens
        self._token_usage.completion_tokens += completion_tokens
        self._token_usage.total_tokens += prompt_tokens + completion_tokens
        self._token_usage.cost_estimate += cost
        self._cost_estimate += cost

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', model='{self.default_model}')>"