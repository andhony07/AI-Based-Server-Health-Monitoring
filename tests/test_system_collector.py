"""Unit and integration tests for the System telemetry collector coordinator."""

from __future__ import annotations

import threading
import time
from datetime import timezone
from unittest import mock

import pytest

from app.collectors.system_collector import SystemCollector
from app.core.config import load_config
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)


class TestSystemCollector:
    """Test suite for unified system telemetry collection and periodic loop."""

    def test_collect_returns_unified_metrics_from_local_system(self) -> None:
        """Verify collect coordinates all sub-collectors and returns complete live telemetry."""
        collector = SystemCollector()
        metrics = collector.collect()

        assert isinstance(metrics, SystemMetrics)
        assert metrics.timestamp is not None
        assert metrics.timestamp.tzinfo == timezone.utc

        # CPU metrics
        assert metrics.cpu is not None
        assert isinstance(metrics.cpu, CPUMetrics)
        assert 0.0 <= metrics.cpu.utilization_percent <= 100.0

        # Memory metrics
        assert metrics.memory is not None
        assert isinstance(metrics.memory, MemoryMetrics)
        assert metrics.memory.total_bytes > 0

        # Disk metrics
        assert metrics.disk is not None
        assert isinstance(metrics.disk, DiskMetrics)
        assert len(metrics.disk.partitions) > 0

        # Network metrics
        assert metrics.network is not None
        assert isinstance(metrics.network, NetworkMetrics)

        # Processes
        assert isinstance(metrics.processes, list)
        assert len(metrics.processes) > 0

        # No errors during normal collection
        assert len(metrics.errors) == 0

    def test_serialization_to_dict(self) -> None:
        """Verify SystemMetrics serializes to clean JSON-compatible dictionary."""
        collector = SystemCollector()
        metrics = collector.collect()
        data = metrics.to_dict()

        assert isinstance(data, dict)
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "network" in data
        assert "processes" in data
        assert "errors" in data

    def test_isolated_collector_failure_resilience(self) -> None:
        """Verify failure in one collector does not prevent other collectors from running."""
        mock_cpu = mock.MagicMock()
        mock_cpu.collect.side_effect = RuntimeError("CPU probe failure")

        mock_mem = mock.MagicMock()
        mock_mem.collect.return_value = MemoryMetrics(
            total_bytes=1000, available_bytes=500, used_bytes=500, utilization_percent=50.0
        )

        mock_disk = mock.MagicMock()
        mock_disk.collect.return_value = DiskMetrics(
            partitions=[
                DiskPartitionMetrics(
                    mount_point="C:\\",
                    total_bytes=1000,
                    used_bytes=200,
                    free_bytes=800,
                    utilization_percent=20.0,
                )
            ],
            total_bytes=1000,
            used_bytes=200,
            free_bytes=800,
            utilization_percent=20.0,
        )

        mock_net = mock.MagicMock()
        mock_net.collect.return_value = NetworkMetrics(
            bytes_sent=100,
            bytes_recv=200,
            packets_sent=5,
            packets_recv=10,
            bytes_sent_per_sec=10.0,
            bytes_recv_per_sec=20.0,
        )

        mock_proc = mock.MagicMock()
        mock_proc.collect.side_effect = RuntimeError("Process table inaccessible")

        collector = SystemCollector(
            cpu_collector=mock_cpu,
            memory_collector=mock_mem,
            disk_collector=mock_disk,
            network_collector=mock_net,
            process_collector=mock_proc,
        )

        metrics = collector.collect()

        # Failed collectors
        assert metrics.cpu is None
        assert metrics.processes == []
        assert len(metrics.errors) == 2
        assert any("CPU collection error" in err for err in metrics.errors)
        assert any("Process collection error" in err for err in metrics.errors)

        # Successful collectors still populated
        assert metrics.memory is not None
        assert metrics.memory.total_bytes == 1000
        assert metrics.disk is not None
        assert metrics.disk.total_bytes == 1000
        assert metrics.network is not None
        assert metrics.network.bytes_sent == 100

    def test_run_collection_loop_with_max_iterations(self) -> None:
        """Verify run_collection_loop respects max_iterations and executes cleanly."""
        collector = SystemCollector()
        collected: list[SystemMetrics] = []

        def sample_callback(sample: SystemMetrics) -> None:
            collected.append(sample)

        # Run for exactly 2 iterations with a fast 0.05s interval
        records = collector.run_collection_loop(
            interval=0.05,
            callback=sample_callback,
            max_iterations=2,
        )

        assert len(records) == 2
        assert len(collected) == 2
        assert all(isinstance(r, SystemMetrics) for r in records)

    def test_run_collection_loop_clean_shutdown_via_event(self) -> None:
        """Verify run_collection_loop exits immediately when stop_event is triggered."""
        collector = SystemCollector()
        stop_event = threading.Event()

        # Stop after 0.1 seconds from background thread
        def trigger_stop() -> None:
            time.sleep(0.1)
            stop_event.set()

        timer = threading.Thread(target=trigger_stop, daemon=True)
        timer.start()

        records = collector.run_collection_loop(
            interval=1.0,
            stop_event=stop_event,
        )

        # Should have captured at least 1 record and exited without waiting full 1.0s
        assert len(records) >= 1

    def test_stop_method_sets_internal_event(self) -> None:
        """Verify stop() method sets internal stop event."""
        collector = SystemCollector()
        assert not collector._stop_event.is_set()
        collector.stop()
        assert collector._stop_event.is_set()
