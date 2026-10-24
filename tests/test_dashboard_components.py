"""Unit tests for dashboard components, adapters, and telemetry rendering."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock

import pytest

from app.dashboard.charts.builders import build_resource_breakdown_bar
from app.dashboard.components.metrics_cards import (
    adapt_telemetry_to_record,
    render_metric_cards,
)
from app.database.models import SystemMetricRecord
from app.ml.simulation import DeterministicAnomalySimulator, SimulationScenario
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)


class TestDashboardMetricCards:
    """Test suite for metrics cards and telemetry model adaptation."""

    @pytest.fixture
    def simulator(self) -> DeterministicAnomalySimulator:
        return DeterministicAnomalySimulator()

    @pytest.fixture
    def live_record(self) -> SystemMetricRecord:
        return SystemMetricRecord(
            id=42,
            timestamp=datetime.now(timezone.utc),
            cpu_percent=45.2,
            cpu_logical_cores=8,
            cpu_physical_cores=4,
            memory_total_bytes=16 * 1024 * 1024 * 1024,
            memory_used_bytes=8 * 1024 * 1024 * 1024,
            memory_available_bytes=8 * 1024 * 1024 * 1024,
            memory_percent=50.0,
            disk_total_bytes=500 * 1024 * 1024 * 1024,
            disk_used_bytes=250 * 1024 * 1024 * 1024,
            disk_free_bytes=250 * 1024 * 1024 * 1024,
            disk_percent=50.0,
            network_bytes_sent=1000000,
            network_bytes_recv=2000000,
            network_bytes_sent_per_sec=102400.0,
            network_bytes_recv_per_sec=204800.0,
            process_count=150,
            top_process_pid=1234,
            top_process_name="python.exe",
            top_process_cpu_percent=12.5,
            top_process_memory_percent=3.2,
        )

    def test_adapt_telemetry_to_record_with_simulated_system_metrics(
        self,
        simulator: DeterministicAnomalySimulator,
    ) -> None:
        """Verify adapting a simulated SystemMetrics into a SystemMetricRecord."""
        sim_metrics = simulator.generate_metrics(SimulationScenario.CPU_SPIKE, seed=42)
        assert isinstance(sim_metrics, SystemMetrics)

        record = adapt_telemetry_to_record(sim_metrics)
        assert record is not None
        assert isinstance(record, SystemMetricRecord)
        assert record.id == 0
        assert record.cpu_percent == sim_metrics.cpu.utilization_percent
        assert record.cpu_logical_cores == sim_metrics.cpu.logical_cores
        assert record.memory_percent == sim_metrics.memory.utilization_percent
        assert record.disk_percent == sim_metrics.disk.utilization_percent
        assert record.network_bytes_sent_per_sec == sim_metrics.network.bytes_sent_per_sec
        assert record.process_count == len(sim_metrics.processes)
        assert record.top_process_name == "stress_worker"
        assert record.top_process_cpu_percent is not None and record.top_process_cpu_percent > 80.0

    def test_adapt_telemetry_to_record_with_live_record(
        self,
        live_record: SystemMetricRecord,
    ) -> None:
        """Verify that passing an existing SystemMetricRecord returns it directly."""
        record = adapt_telemetry_to_record(live_record)
        assert record is live_record
        assert record.id == 42
        assert record.cpu_percent == 45.2

    def test_adapt_telemetry_to_record_with_none(self) -> None:
        """Verify None input returns None."""
        assert adapt_telemetry_to_record(None) is None

    def test_adapt_telemetry_to_record_with_dict(self) -> None:
        """Verify dictionary representations are adapted to SystemMetricRecord."""
        d = {
            "id": 99,
            "timestamp": datetime.now(timezone.utc),
            "cpu_percent": 75.0,
            "memory_percent": 60.0,
            "disk_percent": 80.0,
            "network_bytes_sent_per_sec": 5120.0,
            "network_bytes_recv_per_sec": 10240.0,
            "process_count": 80,
            "top_process_name": "worker",
            "top_process_cpu_percent": 30.0,
            "top_process_pid": 555,
        }
        rec = adapt_telemetry_to_record(d)
        assert rec is not None
        assert rec.id == 99
        assert rec.cpu_percent == 75.0
        assert rec.top_process_name == "worker"

    def test_render_metric_cards_with_simulated_system_metrics(
        self,
        simulator: DeterministicAnomalySimulator,
    ) -> None:
        """Regression test: render_metric_cards must accept SystemMetrics without raising AttributeError."""
        sim_metrics = simulator.generate_metrics(SimulationScenario.MEMORY_LEAK, seed=99)

        cols = [mock.MagicMock() for _ in range(6)]
        with (
            mock.patch("streamlit.columns", return_value=cols) as mock_cols,
            mock.patch("streamlit.caption") as mock_cap,
            mock.patch("streamlit.metric") as mock_metric,
        ):
            # Must execute without AttributeError: 'SystemMetrics' object has no attribute 'cpu_percent'
            render_metric_cards(sim_metrics, is_simulated=True)

            mock_cols.assert_called_once_with(6)
            # Verify SIMULATED label was rendered
            assert mock_cap.called
            call_text = mock_cap.call_args[0][0]
            assert "SIMULATED" in call_text

            # 6 metrics rendered (CPU, RAM, Disk Storage, Disk Active Time, Net, Procs)
            assert mock_metric.call_count == 6

    def test_render_metric_cards_with_live_telemetry_path(
        self,
        live_record: SystemMetricRecord,
    ) -> None:
        """Verify that live telemetry path (SystemMetricRecord) continues to function perfectly."""
        cols = [mock.MagicMock() for _ in range(6)]
        with (
            mock.patch("streamlit.columns", return_value=cols),
            mock.patch("streamlit.caption") as mock_cap,
            mock.patch("streamlit.metric") as mock_metric,
        ):
            render_metric_cards(live_record, is_simulated=False)

            # Live telemetry should not display SIMULATED banner
            assert not mock_cap.called
            assert mock_metric.call_count == 6

    def test_render_metric_cards_handles_missing_optional_values_explicitly(self) -> None:
        """Verify that missing optional values display N/A without silent fabrication."""
        sparse_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=None,
            memory=None,
            disk=None,
            network=None,
            processes=[],
        )

        cols = [mock.MagicMock() for _ in range(6)]
        with (
            mock.patch("streamlit.columns", return_value=cols),
            mock.patch("streamlit.metric") as mock_metric,
        ):
            render_metric_cards(sparse_metrics, is_simulated=False)

            assert mock_metric.call_count == 6
            calls = mock_metric.call_args_list

            # CPU: value should be N/A, delta Cores: N/A
            cpu_call = calls[0]
            assert cpu_call.kwargs["value"] == "N/A"
            assert cpu_call.kwargs["delta"] == "Cores: N/A"

            # RAM: value should be N/A, delta N/A
            ram_call = calls[1]
            assert ram_call.kwargs["value"] == "N/A"
            assert ram_call.kwargs["delta"] == "N/A"

            # Disk Storage: value should be N/A, delta N/A
            disk_call = calls[2]
            assert disk_call.kwargs["value"] == "N/A"
            assert disk_call.kwargs["delta"] == "N/A"

            # Disk Active Time: value should be N/A, delta Unavailable
            disk_act_call = calls[3]
            assert disk_act_call.kwargs["value"] == "N/A"
            assert disk_act_call.kwargs["delta"] == "Unavailable"

            # Network: value should be TX N/A, delta RX N/A
            net_call = calls[4]
            assert net_call.kwargs["value"] == "TX N/A"
            assert net_call.kwargs["delta"] == "RX N/A"

            # Processes: value should be 0 Procs, delta Top: N/A (N/A)
            proc_call = calls[5]
            assert proc_call.kwargs["value"] == "0 Procs"
            assert proc_call.kwargs["delta"] == "Top: N/A (N/A)"

    def test_render_metric_cards_none_shows_warning(self) -> None:
        """Verify None telemetry displays warning."""
        with mock.patch("streamlit.warning") as mock_warn:
            render_metric_cards(None)
            mock_warn.assert_called_once()

    def test_build_resource_breakdown_bar_with_system_metrics(
        self,
        simulator: DeterministicAnomalySimulator,
    ) -> None:
        """Verify that build_resource_breakdown_bar safely handles SystemMetrics instances."""
        sim_metrics = simulator.generate_metrics(SimulationScenario.DISK_SATURATION)
        fig = build_resource_breakdown_bar(sim_metrics)
        assert fig is not None
        assert len(fig.data) == 1
        assert list(fig.data[0].x) == ["CPU", "Memory (RAM)", "Disk Storage"]
        assert fig.data[0].y[2] == sim_metrics.disk.utilization_percent
