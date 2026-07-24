"""Enterprise configuration management for different environments."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(Enum):
    """Application environment."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ProviderConfig:
    """Configuration for a finance provider."""
    name: str
    enabled: bool = True
    priority: int = 0
    timeout: float = 30.0
    max_retries: int = 3
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    rate_limit_rps: float = 10.0
    rate_limit_rpm: int = 100
    health_check_interval: int = 60
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 30.0


@dataclass
class CacheConfig:
    """Cache configuration."""
    backend: str = "memory"  # memory or redis
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    memory_max_size: int = 10000
    stock_quote_ttl: int = 30
    historical_price_ttl: int = 600
    currency_rate_ttl: int = 300
    supported_currencies_ttl: int = 86400
    warming_enabled: bool = True
    warming_interval: int = 300


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    default_rps: float = 10.0
    default_rpm: int = 100
    default_rph: int = 1000
    burst_allowance: int = 5


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    enabled: bool = True
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: float = 30.0
    half_open_max_requests: int = 3


@dataclass
class ObservabilityConfig:
    """Observability configuration."""
    metrics_enabled: bool = True
    health_check_interval: int = 30
    logging_level: str = "INFO"
    structured_logging: bool = True


class EnvironmentConfig(BaseSettings, ABC):
    """Base environment configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Environment = Field(default=Environment.DEVELOPMENT)
    app_name: str = "toolbridge-mcp-server"
    debug: bool = False

    # Provider configs
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)

    # Cache
    cache: CacheConfig = Field(default_factory=CacheConfig)

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Circuit breaker
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)

    # Observability
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    # LLM Providers
    cerebras_api_key: Optional[str] = None
    nvidia_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # Finance Provider API Keys
    alpha_vantage_api_key: Optional[str] = None
    twelve_data_api_key: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    polygon_api_key: Optional[str] = None
    currencylayer_api_key: Optional[str] = None

    @abstractmethod
    def get_database_url(self) -> str:
        """Get database connection URL."""
        pass

    @abstractmethod
    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        pass

    def get_provider_config(self, name: str) -> Optional[ProviderConfig]:
        """Get provider configuration by name."""
        return self.providers.get(name)

    def get_enabled_providers(self) -> list[ProviderConfig]:
        """Get all enabled providers sorted by priority."""
        return sorted(
            [p for p in self.providers.values() if p.enabled],
            key=lambda p: p.priority
        )


class DevelopmentConfig(EnvironmentConfig):
    """Development environment configuration."""

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    observability: ObservabilityConfig = Field(default_factory=lambda: ObservabilityConfig(logging_level="DEBUG"))

    def get_database_url(self) -> str:
        return "sqlite:///./dev.db"

    def get_redis_url(self) -> str:
        return "redis://localhost:6379/0"

    def __post_init__(self):
        # Development defaults
        self.providers = {
            "yahoo_finance": ProviderConfig(
                name="yahoo_finance",
                enabled=True,
                priority=1,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=5.0,
                rate_limit_rpm=100,
            ),
            "alpha_vantage": ProviderConfig(
                name="alpha_vantage",
                enabled=bool(self.alpha_vantage_api_key),
                priority=2,
                timeout=30.0,
                max_retries=3,
                api_key=self.alpha_vantage_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=5,  # Free tier
            ),
            "twelve_data": ProviderConfig(
                name="twelve_data",
                enabled=bool(self.twelve_data_api_key),
                priority=3,
                timeout=30.0,
                max_retries=3,
                api_key=self.twelve_data_api_key,
                rate_limit_rps=8.0,
                rate_limit_rpm=60,
            ),
            "finnhub": ProviderConfig(
                name="finnhub",
                enabled=bool(self.finnhub_api_key),
                priority=4,
                timeout=30.0,
                max_retries=3,
                api_key=self.finnhub_api_key,
                rate_limit_rps=10.0,
                rate_limit_rpm=60,
            ),
            "polygon": ProviderConfig(
                name="polygon",
                enabled=bool(self.polygon_api_key),
                priority=5,
                timeout=30.0,
                max_retries=3,
                api_key=self.polygon_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=100,
            ),
            "frankfurter": ProviderConfig(
                name="frankfurter",
                enabled=True,
                priority=1,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=10.0,
                rate_limit_rpm=60,
            ),
            "exchangerate_api": ProviderConfig(
                name="exchangerate_api",
                enabled=True,
                priority=2,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
            "currencylayer": ProviderConfig(
                name="currencylayer",
                enabled=bool(self.currencylayer_api_key),
                priority=3,
                timeout=30.0,
                max_retries=3,
                api_key=self.currencylayer_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
        }


class TestingConfig(EnvironmentConfig):
    """Testing environment configuration."""

    environment: Environment = Environment.TESTING
    debug: bool = True

    def get_database_url(self) -> str:
        return "sqlite:///:memory:"

    def get_redis_url(self) -> str:
        return "redis://localhost:6379/1"

    def __post_init__(self):
        # Testing defaults - minimal providers
        self.providers = {
            "yahoo_finance": ProviderConfig(
                name="yahoo_finance",
                enabled=True,
                priority=1,
                timeout=10.0,
                max_retries=1,
                rate_limit_rps=10.0,
                rate_limit_rpm=100,
            ),
        }
        self.cache = CacheConfig(backend="memory", memory_max_size=1000)
        self.rate_limit = RateLimitConfig(enabled=False)
        self.circuit_breaker = CircuitBreakerConfig(enabled=False)


class StagingConfig(EnvironmentConfig):
    """Staging environment configuration."""

    environment: Environment = Environment.STAGING
    debug: bool = False

    def get_database_url(self) -> str:
        return os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/staging")

    def get_redis_url(self) -> str:
        return os.getenv("REDIS_URL", "redis://localhost:6379/2")

    def __post_init__(self):
        self.providers = {
            "yahoo_finance": ProviderConfig(
                name="yahoo_finance",
                enabled=True,
                priority=1,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=5.0,
                rate_limit_rpm=100,
            ),
            "alpha_vantage": ProviderConfig(
                name="alpha_vantage",
                enabled=bool(self.alpha_vantage_api_key),
                priority=2,
                timeout=30.0,
                max_retries=3,
                api_key=self.alpha_vantage_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
            "twelve_data": ProviderConfig(
                name="twelve_data",
                enabled=bool(self.twelve_data_api_key),
                priority=3,
                timeout=30.0,
                max_retries=3,
                api_key=self.twelve_data_api_key,
                rate_limit_rps=8.0,
                rate_limit_rpm=60,
            ),
            "finnhub": ProviderConfig(
                name="finnhub",
                enabled=bool(self.finnhub_api_key),
                priority=4,
                timeout=30.0,
                max_retries=3,
                api_key=self.finnhub_api_key,
                rate_limit_rps=10.0,
                rate_limit_rpm=60,
            ),
            "polygon": ProviderConfig(
                name="polygon",
                enabled=bool(self.polygon_api_key),
                priority=5,
                timeout=30.0,
                max_retries=3,
                api_key=self.polygon_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=100,
            ),
            "frankfurter": ProviderConfig(
                name="frankfurter",
                enabled=True,
                priority=1,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=10.0,
                rate_limit_rpm=60,
            ),
            "exchangerate_api": ProviderConfig(
                name="exchangerate_api",
                enabled=True,
                priority=2,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
            "currencylayer": ProviderConfig(
                name="currencylayer",
                enabled=bool(self.currencylayer_api_key),
                priority=3,
                timeout=30.0,
                max_retries=3,
                api_key=self.currencylayer_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
        }
        self.cache = CacheConfig(
            backend="redis",
            redis_url=self.get_redis_url(),
            redis_enabled=True,
        )


class ProductionConfig(EnvironmentConfig):
    """Production environment configuration."""

    environment: Environment = Environment.PRODUCTION
    debug: bool = False

    def get_database_url(self) -> str:
        return os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/production")

    def get_redis_url(self) -> str:
        return os.getenv("REDIS_URL", "redis://localhost:6379/3")

    def __post_init__(self):
        self.providers = {
            "yahoo_finance": ProviderConfig(
                name="yahoo_finance",
                enabled=True,
                priority=1,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=5.0,
                rate_limit_rpm=100,
            ),
            "alpha_vantage": ProviderConfig(
                name="alpha_vantage",
                enabled=bool(self.alpha_vantage_api_key),
                priority=2,
                timeout=30.0,
                max_retries=3,
                api_key=self.alpha_vantage_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
            "twelve_data": ProviderConfig(
                name="twelve_data",
                enabled=bool(self.twelve_data_api_key),
                priority=3,
                timeout=30.0,
                max_retries=3,
                api_key=self.twelve_data_api_key,
                rate_limit_rps=8.0,
                rate_limit_rpm=60,
            ),
            "finnhub": ProviderConfig(
                name="finnhub",
                enabled=bool(self.finnhub_api_key),
                priority=4,
                timeout=30.0,
                max_retries=3,
                api_key=self.finnhub_api_key,
                rate_limit_rps=10.0,
                rate_limit_rpm=60,
            ),
            "polygon": ProviderConfig(
                name="polygon",
                enabled=bool(self.polygon_api_key),
                priority=5,
                timeout=30.0,
                max_retries=3,
                api_key=self.polygon_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=100,
            ),
            "frankfurter": ProviderConfig(
                name="frankfurter",
                enabled=True,
                priority=1,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=10.0,
                rate_limit_rpm=60,
            ),
            "exchangerate_api": ProviderConfig(
                name="exchangerate_api",
                enabled=True,
                priority=2,
                timeout=30.0,
                max_retries=3,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
            "currencylayer": ProviderConfig(
                name="currencylayer",
                enabled=bool(self.currencylayer_api_key),
                priority=3,
                timeout=30.0,
                max_retries=3,
                api_key=self.currencylayer_api_key,
                rate_limit_rps=5.0,
                rate_limit_rpm=30,
            ),
        }
        self.cache = CacheConfig(
            backend="redis",
            redis_url=self.get_redis_url(),
            redis_enabled=True,
        )


# Configuration factory
def get_config() -> EnvironmentConfig:
    """Get configuration for current environment."""
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return ProductionConfig()
    elif env == "staging":
        return StagingConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()


# Global config instance
_config: Optional[EnvironmentConfig] = None


def get_settings() -> EnvironmentConfig:
    """Get global settings instance."""
    global _config
    if _config is None:
        _config = get_config()
    return _config


def reload_settings() -> EnvironmentConfig:
    """Reload settings from environment."""
    global _config
    _config = get_config()
    return _config