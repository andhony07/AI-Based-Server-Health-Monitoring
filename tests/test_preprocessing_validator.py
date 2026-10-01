"""Unit tests for the telemetry MetricsValidator."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

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
from app.preprocessing.validator import MetricsValidator, ValidationResult


class TestMetricsValidator:
    """Test suite for telemetry data validation."""

    def setup_method(self) -> None:
        """Create a standard valid SystemMetrics instance for testing."""
        self.validator = MetricsValidator()
        self.valid_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(
                utilization_percent=25.0,
                logical_cores=4,
                physical_cores=2,
                per_core_percent=[20.0, 30.0, 22.0, 28.0],
            ),
            memory=MemoryMetrics(
                total_bytes=16 * 1024 * 1024 * 1024,
                available_bytes=8 * 1024 * 1024 * 1024,
                used_bytes=8 * 1024 * 1024 * 1024,
                utilization_percent=50.0,
            ),
            disk=DiskMetrics(
                partitions=[
                    DiskPartitionMetrics(
                        mount_point="C:\\",
                        total_bytes=500 * 1024**3,
                        used_bytes=250 * 1024**3,
                        free_bytes=250 * 1024**3,
                        utilization_percent=50.0,
                    )
                ],
                total_bytes=500 * 1024**3,
                used_bytes=250 * 1024**3,
                free_bytes=250 * 1024**3,
                utilization_percent=50.0,
            ),
            network=NetworkMetrics(
                bytes_sent=1000,
                bytes_recv=2000,
                packets_sent=10,
                packets_recv=20,
                bytes_sent_per_sec=100.0,
                bytes_recv_per_sec=200.0,
            ),
            processes=[
                ProcessMetrics(
                    pid=1234,
                    name="python.exe",
                    cpu_percent=5.0,
                    memory_percent=2.5,
                    status="running",
                )
            ],
        )

    def test_valid_metrics_pass_validation(self) -> None:
        """Verify normal, bounded telemetry passes validation with zero issues."""
        res = self.validator.validate(self.valid_metrics)
        assert isinstance(res, ValidationResult)
        assert res.is_valid is True
        assert res.has_issues is False
        assert len(res.issues) == 0

    def test_invalid_type_fails_validation(self) -> None:
        """Verify passing a non-SystemMetrics object generates an error-level validation failure."""
        res = self.validator.validate({"cpu": 50.0})
        assert res.is_valid is False
        assert res.has_errors is True
        assert len(res.issues) == 1
        assert res.issues[0].issue_type == "invalid_type"

    def test_missing_domains_flagged_as_warnings(self) -> None:
        """Verify missing domains generate warnings but do not fail the entire validation."""
        metrics_with_none = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=None,
            memory=None,
            disk=None,
            network=None,
            processes=None,
        )
        res = self.validator.validate(metrics_with_none)
        assert res.is_valid is True  # Warning severity does not mark structural failure
        assert res.has_issues is True
        assert len(res.issues) == 5
        domains = {i.domain for i in res.issues}
        assert domains == {"cpu", "memory", "disk", "network", "process"}

    def test_out_of_range_cpu_utilization(self) -> None:
        """Verify negative or >100% CPU utilization is flagged."""
        bad_cpu_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(
                utilization_percent=150.0,
                logical_cores=4,
                physical_cores=2,
                per_core_percent=[-5.0, 50.0],
            ),
        )
        res = self.validator.validate(bad_cpu_metrics)
        cpu_issues = res.get_issues_for_domain("cpu")
        assert len(cpu_issues) == 2
        assert any("150.0" in i.message for i in cpu_issues)
        assert any("-5.0" in i.message for i in cpu_issues)

    def test_non_finite_nan_and_inf_detected(self) -> None:
        """Verify NaN and infinity in numeric fields are captured as validation issues."""
        nan_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(
                utilization_percent=float("nan"),
                logical_cores=4,
            ),
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=500,
                used_bytes=500,
                utilization_percent=float("inf"),
            ),
            network=NetworkMetrics(
                bytes_sent=100,
                bytes_recv=100,
                packets_sent=1,
                packets_recv=1,
                bytes_sent_per_sec=float("-inf"),
                bytes_recv_per_sec=float("nan"),
            ),
        )
        res = self.validator.validate(nan_metrics)
        assert res.has_issues is True
        non_finite_issues = [i for i in res.issues if i.issue_type == "non_finite"]
        assert len(non_finite_issues) >= 4

    def test_far_future_timestamp_flagged(self) -> None:
        """Verify timestamps far in the future generate a validation issue."""
        future_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc) + timedelta(days=5),
            cpu=self.valid_metrics.cpu,
        )
        res = self.validator.validate(future_metrics)
        sys_issues = res.get_issues_for_domain("system")
        assert any("in the future" in i.message for i in sys_issues)
