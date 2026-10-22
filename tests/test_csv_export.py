"""Tests for CSV telemetry and anomaly export methods in DashboardService.

Validates RFC-4180 standard formatting, header consistency, 39-feature schema exports,
and graceful handling of empty or filtered query subsets.
"""

from __future__ import annotations

import csv
import io
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.config import load_config
from app.dashboard.services.dashboard_service import DashboardService
from app.database.schema import FEATURE_COLUMNS
from app.database.service import PersistenceService
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.preprocessing.pipeline import PreprocessingPipeline


@pytest.fixture
def service_with_samples(tmp_path: Path) -> DashboardService:
    settings = load_config(
        database_path=tmp_path / "csv_test.db",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
    )
    svc = DashboardService(settings=settings)

    base_time = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    for i in range(5):
        ts = base_time + timedelta(minutes=i)
        sample = SystemMetrics(
            timestamp=ts,
            cpu=CPUMetrics(utilization_percent=20.0 + i * 5, logical_cores=4),
            memory=MemoryMetrics(
                total_bytes=16 * 1024**3,
                available_bytes=(16 - 4 - i) * 1024**3,
                used_bytes=(4 + i) * 1024**3,
                utilization_percent=25.0 + i * 5,
            ),
            disk=DiskMetrics(
                partitions=[],
                total_bytes=100 * 1024**3,
                used_bytes=40 * 1024**3,
                free_bytes=60 * 1024**3,
                utilization_percent=40.0,
            ),
            network=NetworkMetrics(
                bytes_sent=1000 * (i + 1),
                bytes_recv=2000 * (i + 1),
                packets_sent=10,
                packets_recv=20,
                bytes_sent_per_sec=1024.0 * (i + 1),
                bytes_recv_per_sec=2048.0 * (i + 1),
            ),
            processes=[
                ProcessMetrics(pid=100 + i, name=f"app_{i}", cpu_percent=10.0 + i, memory_percent=5.0, status="running")
            ],
        )
        proc = svc.pipeline.process(sample)
        svc.persistence.persist_sample(sample, proc)

    return svc


def test_export_metrics_csv_headers_and_data(service_with_samples: DashboardService) -> None:
    """Verify metrics CSV output has standard headers and expected row count."""
    csv_str = service_with_samples.export_metrics_csv()
    assert isinstance(csv_str, str)
    assert len(csv_str) > 0

    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    # 1 header + 5 data rows
    assert len(rows) == 6

    headers = rows[0]
    expected_headers = [
        "id",
        "timestamp_utc",
        "cpu_percent",
        "cpu_logical_cores",
        "memory_percent",
        "memory_used_mb",
        "memory_available_mb",
        "memory_total_mb",
        "disk_percent",
        "disk_used_gb",
        "disk_free_gb",
        "disk_total_gb",
        "network_bytes_sent_per_sec",
        "network_bytes_recv_per_sec",
        "process_count",
        "top_process_name",
        "top_process_pid",
        "top_process_cpu_percent",
        "top_process_memory_percent",
    ]
    assert headers == expected_headers

    # Verify first data row
    first_row = rows[1]
    assert first_row[0] == "1"
    assert first_row[2] == "20.0"
    assert first_row[15] == "app_0"


def test_export_metrics_csv_empty_database(tmp_path: Path) -> None:
    """Verify empty database returns headers without crashing."""
    settings = load_config(
        database_path=tmp_path / "empty.db",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
    )
    svc = DashboardService(settings=settings)

    csv_str = svc.export_metrics_csv()
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    # Exactly 1 header row, 0 data rows
    assert len(rows) == 1
    assert rows[0][0] == "id"


def test_export_metrics_csv_time_filtering(service_with_samples: DashboardService) -> None:
    """Verify start_time and end_time restrict CSV rows."""
    base_time = datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
    start = base_time + timedelta(minutes=1)
    end = base_time + timedelta(minutes=3)

    csv_str = service_with_samples.export_metrics_csv(start_time=start, end_time=end)
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    # 1 header + 3 filtered rows
    assert len(rows) == 4


def test_export_anomalies_csv(service_with_samples: DashboardService) -> None:
    """Verify anomaly audit log CSV contains expected anomaly scoring columns."""
    csv_str = service_with_samples.export_anomalies_csv()
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    assert len(rows) == 6
    headers = rows[0]
    assert "anomaly_score" in headers
    assert "is_anomaly" in headers
    assert "risk_category" in headers
    assert "health_score" in headers


def test_export_features_csv_all_39_features(service_with_samples: DashboardService) -> None:
    """Verify feature vector CSV includes all 39 numerical feature columns."""
    csv_str = service_with_samples.export_features_csv()
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)

    assert len(rows) == 6
    headers = rows[0]

    # Prefix columns: feature_id, timestamp_utc, metric_id
    assert headers[:3] == ["feature_id", "timestamp_utc", "metric_id"]

    # Trailing 39 columns must match FEATURE_COLUMNS exactly
    feature_cols = headers[3:]
    assert len(feature_cols) == 39
    assert tuple(feature_cols) == FEATURE_COLUMNS
