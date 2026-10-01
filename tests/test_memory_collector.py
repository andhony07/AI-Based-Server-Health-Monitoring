"""Unit and integration tests for the Memory telemetry collector."""

from __future__ import annotations

from unittest import mock

import pytest

from app.collectors.memory_collector import MemoryCollector
from app.models.metrics import MemoryMetrics


class TestMemoryCollector:
    """Test suite for memory telemetry collection."""

    def test_collect_returns_valid_metrics_structure(self) -> None:
        """Verify collect returns a properly structured MemoryMetrics object."""
        collector = MemoryCollector()
        metrics = collector.collect()

        assert isinstance(metrics, MemoryMetrics)
        assert isinstance(metrics.total_bytes, int)
        assert metrics.total_bytes > 0
        assert isinstance(metrics.available_bytes, int)
        assert metrics.available_bytes > 0
        assert isinstance(metrics.used_bytes, int)
        assert metrics.used_bytes > 0
        assert isinstance(metrics.utilization_percent, float)
        assert 0.0 <= metrics.utilization_percent <= 100.0

        # Validate MB helper properties
        assert metrics.total_mb > 0
        assert metrics.used_mb > 0
        assert metrics.available_mb > 0

    @mock.patch("psutil.virtual_memory")
    def test_mocked_memory_metrics(self, mock_vm: mock.MagicMock) -> None:
        """Verify exact byte extraction and percent calculation with mock values."""
        mock_obj = mock.MagicMock()
        mock_obj.total = 16 * 1024 * 1024 * 1024  # 16 GB
        mock_obj.available = 8 * 1024 * 1024 * 1024  # 8 GB
        mock_obj.used = 8 * 1024 * 1024 * 1024  # 8 GB
        mock_obj.percent = 50.0
        mock_vm.return_value = mock_obj

        collector = MemoryCollector()
        metrics = collector.collect()

        assert metrics.total_bytes == 17179869184
        assert metrics.available_bytes == 8589934592
        assert metrics.used_bytes == 8589934592
        assert metrics.utilization_percent == 50.0
        assert metrics.total_mb == 16384.0
        assert metrics.used_mb == 8192.0

    @mock.patch("psutil.virtual_memory", side_effect=OSError("Cannot read memory info"))
    def test_error_handling_raises_runtime_error(self, _mock_vm: mock.MagicMock) -> None:
        """Verify memory query failures raise RuntimeError."""
        collector = MemoryCollector()
        with pytest.raises(RuntimeError, match="Memory telemetry collection error"):
            collector.collect()
