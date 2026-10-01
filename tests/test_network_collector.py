"""Unit and integration tests for the Network telemetry collector."""

from __future__ import annotations

from unittest import mock

import pytest

from app.collectors.network_collector import NetworkCollector
from app.models.metrics import NetworkMetrics


class TestNetworkCollector:
    """Test suite for network traffic and throughput telemetry."""

    def test_collect_returns_valid_metrics_structure(self) -> None:
        """Verify collect returns valid NetworkMetrics with real host counters."""
        collector = NetworkCollector()
        metrics = collector.collect()

        assert isinstance(metrics, NetworkMetrics)
        assert isinstance(metrics.bytes_sent, int)
        assert metrics.bytes_sent >= 0
        assert isinstance(metrics.bytes_recv, int)
        assert metrics.bytes_recv >= 0
        assert isinstance(metrics.packets_sent, int)
        assert metrics.packets_sent >= 0
        assert isinstance(metrics.packets_recv, int)
        assert metrics.packets_recv >= 0

        # First sample has no baseline, so throughput is 0.0
        assert metrics.bytes_sent_per_sec == 0.0
        assert metrics.bytes_recv_per_sec == 0.0
        assert metrics.upload_kbps == 0.0
        assert metrics.download_kbps == 0.0

    @mock.patch("time.monotonic")
    @mock.patch("psutil.net_io_counters")
    def test_throughput_calculation_between_samples(
        self, mock_counters: mock.MagicMock, mock_time: mock.MagicMock
    ) -> None:
        """Verify upload and download rates are correctly computed across successive samples."""
        c1 = mock.MagicMock(
            bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20
        )
        c2 = mock.MagicMock(
            bytes_sent=3000, bytes_recv=6000, packets_sent=20, packets_recv=40
        )
        mock_counters.side_effect = [c1, c2]
        mock_time.side_effect = [100.0, 102.0]  # 2.0s elapsed

        collector = NetworkCollector()

        # Sample 1
        m1 = collector.collect()
        assert m1.bytes_sent_per_sec == 0.0
        assert m1.bytes_recv_per_sec == 0.0

        # Sample 2: (3000 - 1000) / 2.0 = 1000 B/s sent, (6000 - 2000) / 2.0 = 2000 B/s recv
        m2 = collector.collect()
        assert m2.bytes_sent == 3000
        assert m2.bytes_recv == 6000
        assert m2.bytes_sent_per_sec == 1000.0
        assert m2.bytes_recv_per_sec == 2000.0
        assert m2.upload_kbps == round(1000.0 / 1024.0, 2)
        assert m2.download_kbps == round(2000.0 / 1024.0, 2)

    @mock.patch("time.monotonic")
    @mock.patch("psutil.net_io_counters")
    def test_counter_reset_handled_safely(
        self, mock_counters: mock.MagicMock, mock_time: mock.MagicMock
    ) -> None:
        """Verify counter reset or interface restart does not produce negative rates."""
        c1 = mock.MagicMock(
            bytes_sent=50000, bytes_recv=50000, packets_sent=100, packets_recv=100
        )
        c2 = mock.MagicMock(
            bytes_sent=100, bytes_recv=200, packets_sent=1, packets_recv=2
        )  # Reset occurred
        mock_counters.side_effect = [c1, c2]
        mock_time.side_effect = [100.0, 101.0]

        collector = NetworkCollector()
        collector.collect()
        m2 = collector.collect()

        assert m2.bytes_sent_per_sec == 0.0
        assert m2.bytes_recv_per_sec == 0.0

    @mock.patch("time.monotonic")
    @mock.patch("psutil.net_io_counters")
    def test_zero_elapsed_time_avoids_division_by_zero(
        self, mock_counters: mock.MagicMock, mock_time: mock.MagicMock
    ) -> None:
        """Verify back-to-back calls with 0 elapsed time avoid division by zero."""
        c1 = mock.MagicMock(
            bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20
        )
        c2 = mock.MagicMock(
            bytes_sent=1500, bytes_recv=2500, packets_sent=15, packets_recv=25
        )
        mock_counters.side_effect = [c1, c2]
        mock_time.side_effect = [50.0, 50.0]  # 0.0 elapsed

        collector = NetworkCollector()
        collector.collect()
        m2 = collector.collect()

        assert m2.bytes_sent_per_sec == 0.0
        assert m2.bytes_recv_per_sec == 0.0

    @mock.patch("psutil.net_io_counters", return_value=None)
    def test_null_counters_raises_runtime_error(
        self, _mock_counters: mock.MagicMock
    ) -> None:
        """Verify null network counters raise RuntimeError."""
        collector = NetworkCollector()
        with pytest.raises(RuntimeError, match="Host OS returned null network counters"):
            collector.collect()
