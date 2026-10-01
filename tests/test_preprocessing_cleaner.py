"""Unit tests for the telemetry MetricsCleaner."""

from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.preprocessing.cleaner import CleanedSystemMetrics, MetricsCleaner
from app.preprocessing.validator import MetricsValidator


class TestMetricsCleaner:
    """Test suite for data cleaning and imputation."""

    def setup_method(self) -> None:
        """Initialize cleaner and validator instances."""
        self.cleaner = MetricsCleaner(missing_value_strategy="zero")
        self.validator = MetricsValidator()

    def test_clean_sanitizes_out_of_bounds_percentages(self) -> None:
        """Verify percentages above 100 or below 0 are clamped to [0.0, 100.0]."""
        metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(
                utilization_percent=125.0,  # Out of bounds high
                logical_cores=4,
                per_core_percent=[-15.0, 150.0],
            ),
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=500,
                used_bytes=500,
                utilization_percent=-10.0,  # Out of bounds low
            ),
        )
        val_res = self.validator.validate(metrics)
        cleaned = self.cleaner.clean(metrics, val_res)

        assert isinstance(cleaned, CleanedSystemMetrics)
        assert cleaned.cpu_percent == 100.0
        assert cleaned.per_core_percent == [0.0, 100.0]
        assert cleaned.memory_percent == 0.0

    def test_clean_converts_nan_and_inf_to_safe_values(self) -> None:
        """Verify NaN, +inf, -inf are replaced with safe zero values."""
        metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(
                utilization_percent=float("nan"),
                logical_cores=4,
            ),
            network=NetworkMetrics(
                bytes_sent=100,
                bytes_recv=100,
                packets_sent=1,
                packets_recv=1,
                bytes_sent_per_sec=float("inf"),
                bytes_recv_per_sec=float("-inf"),
            ),
        )
        val_res = self.validator.validate(metrics)
        cleaned = self.cleaner.clean(metrics, val_res)

        assert not math.isnan(cleaned.cpu_percent)
        assert not math.isinf(cleaned.cpu_percent)
        assert cleaned.cpu_percent == 0.0

        assert not math.isinf(cleaned.network_sent_bytes_per_sec)
        assert not math.isinf(cleaned.network_recv_bytes_per_sec)
        assert cleaned.network_sent_bytes_per_sec == 0.0
        assert cleaned.network_recv_bytes_per_sec == 0.0

    def test_missing_domains_set_quality_indicators(self) -> None:
        """Verify missing domains produce 1.0 quality indicators while valid domains produce 0.0."""
        metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=42.0, logical_cores=4),
            memory=None,
            disk=None,
            network=None,
            processes=None,
        )
        val_res = self.validator.validate(metrics)
        cleaned = self.cleaner.clean(metrics, val_res)

        assert cleaned.cpu_percent == 42.0
        assert cleaned.is_cpu_missing == 0.0
        assert cleaned.is_memory_missing == 1.0
        assert cleaned.is_disk_missing == 1.0
        assert cleaned.is_network_missing == 1.0
        assert cleaned.is_processes_missing == 1.0

    def test_last_valid_imputation_strategy(self) -> None:
        """Verify 'last_valid' strategy carries forward previous readings when domain fails."""
        cleaner = MetricsCleaner(missing_value_strategy="last_valid")

        # 1. First valid sample
        m1 = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=55.0, logical_cores=8),
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=400,
                used_bytes=600,
                utilization_percent=60.0,
            ),
        )
        c1 = cleaner.clean(m1, self.validator.validate(m1))
        assert c1.cpu_percent == 55.0

        # 2. Second sample where CPU probe temporarily drops
        m2 = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=None,  # Missing!
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=350,
                used_bytes=650,
                utilization_percent=65.0,
            ),
        )
        c2 = cleaner.clean(m2, self.validator.validate(m2))
        assert c2.cpu_percent == 55.0  # Retained from last valid sample
        assert c2.is_cpu_missing == 1.0  # Still flagged as missing for ML awareness
        assert c2.memory_percent == 65.0
