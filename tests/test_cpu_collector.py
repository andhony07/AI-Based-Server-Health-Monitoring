"""Unit and integration tests for the CPU telemetry collector."""

from __future__ import annotations

from unittest import mock

import pytest

from app.collectors.cpu_collector import CPUCollector
from app.models.metrics import CPUMetrics


class TestCPUCollector:
    """Test suite for CPU telemetry collection."""

    def test_collect_returns_valid_metrics_structure(self) -> None:
        """Verify collect returns a properly structured CPUMetrics object."""
        collector = CPUCollector()
        metrics = collector.collect()

        assert isinstance(metrics, CPUMetrics)
        assert isinstance(metrics.utilization_percent, float)
        assert 0.0 <= metrics.utilization_percent <= 100.0
        assert isinstance(metrics.logical_cores, int)
        assert metrics.logical_cores >= 1

        if metrics.physical_cores is not None:
            assert isinstance(metrics.physical_cores, int)
            assert metrics.physical_cores >= 1

        assert isinstance(metrics.per_core_percent, list)
        assert len(metrics.per_core_percent) == metrics.logical_cores
        for core_pct in metrics.per_core_percent:
            assert isinstance(core_pct, float)
            assert 0.0 <= core_pct <= 100.0

    @mock.patch("psutil.cpu_percent")
    @mock.patch("psutil.cpu_count")
    def test_mocked_cpu_metrics(
        self, mock_count: mock.MagicMock, mock_percent: mock.MagicMock
    ) -> None:
        """Verify metric calculation using mocked psutil values."""
        def mock_cpu(interval: object = None, percpu: bool = False) -> object:
            if percpu:
                return [40.0, 51.0]
            return 45.5

        mock_percent.side_effect = mock_cpu
        mock_count.side_effect = lambda logical: 2 if logical else 1

        collector = CPUCollector(sample_interval=0.1)
        metrics = collector.collect()

        assert metrics.utilization_percent == 45.5
        assert metrics.logical_cores == 2
        assert metrics.physical_cores == 1
        assert metrics.per_core_percent == [40.0, 51.0]

    @mock.patch("psutil.cpu_percent", side_effect=PermissionError("CPU access denied"))
    def test_error_handling_raises_runtime_error(
        self, _mock_percent: mock.MagicMock
    ) -> None:
        """Verify collection errors are caught, logged, and raised as RuntimeError."""
        collector = CPUCollector()
        with pytest.raises(RuntimeError, match="CPU telemetry collection error"):
            collector.collect()
