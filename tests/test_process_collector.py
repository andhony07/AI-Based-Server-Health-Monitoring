"""Unit and integration tests for the Process telemetry collector."""

from __future__ import annotations

from unittest import mock

import psutil
import pytest

from app.collectors.process_collector import ProcessCollector
from app.models.metrics import ProcessMetrics


class TestProcessCollector:
    """Test suite for process telemetry collection."""

    def test_collect_returns_valid_metrics_structure(self) -> None:
        """Verify collect returns top monitored processes with valid fields."""
        collector = ProcessCollector(max_processes=5)
        processes = collector.collect()

        assert isinstance(processes, list)
        assert len(processes) <= 5
        assert len(processes) > 0

        for proc in processes:
            assert isinstance(proc, ProcessMetrics)
            assert isinstance(proc.pid, int)
            assert proc.pid >= 0
            assert isinstance(proc.name, str)
            assert len(proc.name) > 0
            assert isinstance(proc.cpu_percent, float)
            assert proc.cpu_percent >= 0.0
            assert isinstance(proc.memory_percent, float)
            assert proc.memory_percent >= 0.0
            assert isinstance(proc.status, str)

    @mock.patch("psutil.process_iter")
    def test_sorting_and_max_processes_limit(
        self, mock_iter: mock.MagicMock
    ) -> None:
        """Verify processes are sorted by resource consumption and capped by max_processes."""
        p1 = mock.MagicMock(
            info={"pid": 101, "name": "idle.exe", "cpu_percent": 1.0, "memory_percent": 2.0, "status": "running"}
        )
        p2 = mock.MagicMock(
            info={"pid": 102, "name": "busy.exe", "cpu_percent": 85.0, "memory_percent": 10.0, "status": "running"}
        )
        p3 = mock.MagicMock(
            info={"pid": 103, "name": "medium.exe", "cpu_percent": 25.0, "memory_percent": 5.0, "status": "running"}
        )
        mock_iter.return_value = [p1, p2, p3]

        collector = ProcessCollector(max_processes=2)
        processes = collector.collect()

        assert len(processes) == 2
        assert processes[0].pid == 102
        assert processes[0].name == "busy.exe"
        assert processes[0].cpu_percent == 85.0
        assert processes[1].pid == 103
        assert processes[1].name == "medium.exe"
        assert processes[1].cpu_percent == 25.0

    @mock.patch("psutil.process_iter")
    def test_inaccessible_and_terminated_processes_handled_gracefully(
        self, mock_iter: mock.MagicMock
    ) -> None:
        """Verify AccessDenied, NoSuchProcess, and ZombieProcess exceptions are handled cleanly."""
        good_proc = mock.MagicMock(
            info={"pid": 200, "name": "valid.exe", "cpu_percent": 12.0, "memory_percent": 4.0, "status": "running"}
        )

        class FaultyProc:
            @property
            def info(self) -> dict[str, object]:
                raise psutil.AccessDenied(pid=999)

        class TerminatedProc:
            @property
            def info(self) -> dict[str, object]:
                raise psutil.NoSuchProcess(pid=998)

        class ZombieProc:
            @property
            def info(self) -> dict[str, object]:
                raise psutil.ZombieProcess(pid=997)

        mock_iter.return_value = [FaultyProc(), good_proc, TerminatedProc(), ZombieProc()]

        collector = ProcessCollector(max_processes=10)
        processes = collector.collect()

        assert len(processes) == 1
        assert processes[0].pid == 200
        assert processes[0].name == "valid.exe"

    @mock.patch("psutil.process_iter", side_effect=OSError("OS Process Table Corrupt"))
    def test_process_table_failure_raises_runtime_error(
        self, _mock_iter: mock.MagicMock
    ) -> None:
        """Verify fatal process table query errors raise RuntimeError."""
        collector = ProcessCollector()
        with pytest.raises(RuntimeError, match="Process table enumeration failed"):
            collector.collect()
