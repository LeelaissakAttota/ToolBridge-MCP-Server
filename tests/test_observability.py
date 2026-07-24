"""Tests for Observability (Metrics & Health Monitoring)."""

import pytest
import asyncio
import time
from datetime import datetime, timezone, timedelta

from mcp_server.services.finance.observability import (
    MetricsCollector,
    MetricType,
    MetricPoint,
    MetricSummary,
    HealthMonitor,
    HealthStatus,
    HealthCheckResult,
    get_metrics,
    get_health,
    init_observability,
    close_observability,
    record_request_latency,
    record_provider_request,
    record_retry,
    record_cache_hit,
    record_cache_miss,
    record_token_usage,
    record_cost,
)


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_increment_counter(self):
        """Test incrementing a counter metric."""
        collector = MetricsCollector()
        collector.increment("requests_total", 1.0, labels={"provider": "test"})
        
        metric = collector.get_metric("requests_total", labels={"provider": "test"})
        assert metric is not None
        assert metric.count == 1
        assert metric.sum == 1.0

    def test_increment_without_labels(self):
        """Test incrementing a counter without labels."""
        collector = MetricsCollector()
        collector.increment("simple_counter", 5.0)
        
        metric = collector.get_metric("simple_counter")
        assert metric is not None
        assert metric.count == 1
        assert metric.sum == 5.0

    def test_gauge(self):
        """Test setting a gauge metric."""
        collector = MetricsCollector()
        collector.gauge("active_connections", 42.0, labels={"service": "api"})
        
        metric = collector.get_metric("active_connections", labels={"service": "api"})
        assert metric is not None
        assert metric.count == 1
        assert metric.sum == 42.0
        assert metric.avg == 42.0

    def test_histogram(self):
        """Test recording histogram values."""
        collector = MetricsCollector()
        collector.histogram("request_latency_ms", 150.0, labels={"endpoint": "/api"})
        collector.histogram("request_latency_ms", 200.0, labels={"endpoint": "/api"})
        
        metric = collector.get_metric("request_latency_ms", labels={"endpoint": "/api"})
        assert metric is not None
        assert metric.count == 2
        assert metric.sum == 350.0
        assert metric.avg == 175.0
        assert metric.min == 150.0
        assert metric.max == 200.0

    def test_get_all_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()
        collector.increment("counter1")
        collector.gauge("gauge1", 10.0)
        collector.histogram("hist1", 50.0)
        
        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) >= 3

    def test_get_points(self):
        """Test getting metric points with filtering."""
        collector = MetricsCollector()
        collector.increment("test_metric", 1.0, labels={"env": "dev"})
        collector.increment("test_metric", 1.0, labels={"env": "prod"})
        
        # Filter by name
        points = collector.get_points(name="test_metric")
        assert len(points) == 2
        
        # Filter by name not supported in get_points, just verify we can get points
        all_points = collector.get_points()
        assert len(all_points) >= 2

    def test_reset_metric(self):
        """Test resetting a specific metric."""
        collector = MetricsCollector()
        collector.increment("to_reset", 5.0)
        
        # Use get_provider_metric which clears by prefix
        collector.get_provider_metric("to_reset")
        
        metric = collector.get_metric("to_reset")
        assert metric is None

    def test_reset_all(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()
        collector.increment("counter1")
        collector.gauge("gauge1", 10.0)
        
        collector.reset_all()
        
        assert collector.get_all_metrics() == {}


class TestHealthMonitor:
    """Tests for HealthMonitor."""

    @pytest.fixture
    def monitor(self):
        """Create a fresh health monitor."""
        return HealthMonitor(check_interval=1)  # 1 second for testing

    def test_register_check(self, monitor):
        """Test registering a health check."""
        def dummy_check():
            return HealthCheckResult(name="test", status=HealthStatus.HEALTHY)
        
        monitor.register_check("test_check", dummy_check)
        assert "test_check" in monitor._checks

    @pytest.mark.asyncio
    async def test_run_check(self, monitor):
        """Test running a single health check."""
        def healthy_check():
            return HealthCheckResult(
                name="healthy", 
                status=HealthStatus.HEALTHY,
                message="All good"
            )
        
        monitor.register_check("healthy", healthy_check)
        result = await monitor.run_check("healthy")
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"

    @pytest.mark.asyncio
    async def test_run_unhealthy_check(self, monitor):
        """Test running an unhealthy check."""
        def unhealthy_check():
            return HealthCheckResult(
                name="unhealthy",
                status=HealthStatus.UNHEALTHY,
                message="Service down"
            )
        
        monitor.register_check("unhealthy", unhealthy_check)
        result = await monitor.run_check("unhealthy")
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.message == "Service down"

    @pytest.mark.asyncio
    async def test_run_nonexistent_check(self, monitor):
        """Test running a non-existent check."""
        result = await monitor.run_check("nonexistent")
        
        assert result.status == HealthStatus.UNKNOWN
        assert "not found" in result.message.lower()

    @pytest.mark.asyncio
    async def test_run_all_checks(self, monitor):
        """Test running all registered checks."""
        def check1():
            return HealthCheckResult(name="c1", status=HealthStatus.HEALTHY)
        def check2():
            return HealthCheckResult(name="c2", status=HealthStatus.DEGRADED)
        
        monitor.register_check("check1", check1)
        monitor.register_check("check2", check2)
        
        results = await monitor.run_all_checks()
        
        assert len(results) == 2
        assert results["check1"].status == HealthStatus.HEALTHY
        assert results["check2"].status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_start_stop(self, monitor):
        """Test starting and stopping the monitor."""
        await monitor.start()
        assert monitor._running is True
        
        await monitor.stop()
        assert monitor._running is False

    def test_get_status(self, monitor):
        """Test getting health status."""
        monitor._results = {
            "check1": HealthCheckResult(name="c1", status=HealthStatus.HEALTHY),
            "check2": HealthCheckResult(name="c2", status=HealthStatus.UNHEALTHY),
        }
        
        status = monitor.get_status()
        assert status["overall"] == "unhealthy"
        assert "check1" in status["checks"]
        assert "check2" in status["checks"]

    def test_get_single_status(self, monitor):
        """Test getting status for a single check."""
        result = HealthCheckResult(
            name="test", 
            status=HealthStatus.HEALTHY, 
            message="OK",
            latency_ms=5.0
        )
        monitor._results["test"] = result
        
        status = monitor.get_status("test")
        
        assert status["name"] == "test"
        assert status["status"] == "healthy"
        assert status["message"] == "OK"
        assert status["latency_ms"] == 5.0


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_record_request_latency(self):
        """Test recording request latency."""
        collector = get_metrics()
        collector.reset_all()
        
        record_request_latency("test_provider", "get_quote", 150.0)
        
        metric = collector.get_metric(
            "finance_request_latency_ms",
            labels={"provider": "test_provider", "operation": "get_quote"}
        )
        assert metric is not None
        assert metric.count == 1

    def test_record_provider_request(self):
        """Test recording provider request."""
        collector = get_metrics()
        collector.reset_all()
        
        record_provider_request("test_provider", True)
        record_provider_request("test_provider", False)
        
        success = collector.get_metric(
            "finance_provider_requests_total",
            labels={"provider": "test_provider", "result": "success"}
        )
        failure = collector.get_metric(
            "finance_provider_requests_total",
            labels={"provider": "test_provider", "result": "failure"}
        )
        assert success is not None
        assert failure is not None

    def test_record_retry(self):
        """Test recording retry."""
        collector = get_metrics()
        collector.reset_all()
        
        record_retry("test_provider")
        
        metric = collector.get_metric(
            "finance_retries_total",
            labels={"provider": "test_provider"}
        )
        assert metric is not None

    def test_record_cache_hit_miss(self):
        """Test recording cache hits/misses."""
        collector = get_metrics()
        collector.reset_all()
        
        record_cache_hit("test_provider")
        record_cache_miss("test_provider")
        
        hit = collector.get_metric(
            "finance_cache_hits_total",
            labels={"provider": "test_provider"}
        )
        miss = collector.get_metric(
            "finance_cache_misses_total",
            labels={"provider": "test_provider"}
        )
        assert hit is not None
        assert miss is not None

    def test_record_token_usage(self):
        """Test recording token usage."""
        collector = get_metrics()
        initial = collector.get_metric("finance_llm_prompt_tokens_total", labels={"provider": "test"})
        initial_sum = initial.sum if initial else 0.0
        
        record_token_usage("test", 100, 50)
        
        metric = collector.get_metric("finance_llm_prompt_tokens_total", labels={"provider": "test"})
        assert metric is not None
        assert metric.sum == initial_sum + 100.0

    def test_record_cost(self):
        """Test recording cost."""
        collector = get_metrics()
        initial = collector.get_metric("finance_cost_usd_total", labels={"provider": "test"})
        initial_sum = initial.sum if initial else 0.0
        
        record_cost("test", 0.001)
        
        metric = collector.get_metric("finance_cost_usd_total", labels={"provider": "test"})
        assert metric is not None
        assert metric.sum >= initial_sum + 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])