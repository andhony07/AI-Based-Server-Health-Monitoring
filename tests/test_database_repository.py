"""Unit tests for MetricsRepository data access and query operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.database.connection import db_session, get_connection
from app.database.migrations import apply_migrations
from app.database.models import (
    FeatureVectorRecord,
    SystemMetricRecord,
    ValidationLogRecord,
)
from app.database.repository import MetricsRepository
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.preprocessing.feature_engineer import FeatureVector
from app.preprocessing.validator import ValidationIssue, ValidationResult


@pytest.fixture
def repo_db(tmp_path: Path) -> Path:
    """Fixture initializing a clean SQLite database and returning its path."""
    db_path = tmp_path / "repo_test.db"
    with get_connection(db_path) as conn:
        apply_migrations(conn)
    return db_path


@pytest.fixture
def sample_metrics() -> SystemMetrics:
    """Fixture creating a realistic sample SystemMetrics instance."""
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    return SystemMetrics(
        timestamp=now,
        cpu=CPUMetrics(
            utilization_percent=45.5,
            logical_cores=8,
            physical_cores=4,
            per_core_percent=[40.0, 50.0, 45.0, 47.0],
        ),
        memory=MemoryMetrics(
            total_bytes=16 * 1024**3,
            available_bytes=8 * 1024**3,
            used_bytes=8 * 1024**3,
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
            bytes_sent=1000000,
            bytes_recv=2000000,
            packets_sent=5000,
            packets_recv=8000,
            bytes_sent_per_sec=1024.0,
            bytes_recv_per_sec=2048.0,
        ),
        processes=[
            ProcessMetrics(
                pid=1001,
                name="python.exe",
                cpu_percent=25.0,
                memory_percent=5.0,
                status="running",
            ),
            ProcessMetrics(
                pid=1002,
                name="chrome.exe",
                cpu_percent=15.0,
                memory_percent=10.0,
                status="running",
            ),
        ],
        errors=["Simulated non-fatal telemetry warning"],
    )


@pytest.fixture
def sample_feature_vector() -> FeatureVector:
    """Fixture creating a realistic 39-feature vector."""
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    features = {
        "cpu_utilization_percent": 45.5,
        "cpu_utilization_delta": 2.1,
        "cpu_utilization_rolling_mean": 43.0,
        "cpu_utilization_rolling_max": 50.0,
        "cpu_utilization_rolling_min": 35.0,
        "cpu_cores_logical": 8.0,
        "memory_utilization_percent": 50.0,
        "memory_used_mb": 8192.0,
        "memory_available_mb": 8192.0,
        "memory_utilization_delta": 0.5,
        "memory_used_delta_mb": 50.0,
        "memory_utilization_rolling_mean": 49.5,
        "memory_utilization_rolling_max": 52.0,
        "disk_utilization_percent": 50.0,
        "disk_used_gb": 250.0,
        "disk_free_gb": 250.0,
        "disk_utilization_delta": 0.0,
        "disk_utilization_rolling_mean": 50.0,
        "network_bytes_sent_per_sec": 1024.0,
        "network_bytes_recv_per_sec": 2048.0,
        "network_sent_delta_per_sec": 100.0,
        "network_recv_delta_per_sec": 200.0,
        "network_bytes_sent_rolling_mean": 1000.0,
        "network_bytes_recv_rolling_mean": 2000.0,
        "network_bytes_sent_rolling_max": 1500.0,
        "network_bytes_recv_rolling_max": 2500.0,
        "process_count": 2.0,
        "top_process_cpu_percent": 25.0,
        "top_process_memory_percent": 10.0,
        "top_processes_total_cpu_percent": 40.0,
        "top_processes_total_memory_percent": 15.0,
        "sample_interval_sec": 5.0,
        "hour_of_day": 12.0,
        "day_of_week": 3.0,
        "is_cpu_missing": 0.0,
        "is_memory_missing": 0.0,
        "is_disk_missing": 0.0,
        "is_network_missing": 0.0,
        "is_processes_missing": 0.0,
    }
    return FeatureVector(
        timestamp=now,
        features=features,
        metadata={"sample_count": 1, "window_size": 12},
    )


class TestMetricsRepository:
    """Test suite for repository CRUD operations."""

    def test_insert_and_retrieve_system_metrics(
        self,
        repo_db: Path,
        sample_metrics: SystemMetrics,
    ) -> None:
        """Verify inserting raw SystemMetrics returns valid ID and allows full retrieval."""
        repo = MetricsRepository()
        with db_session(repo_db) as session:
            metric_id = repo.insert_system_metrics(session, sample_metrics)

        assert metric_id > 0

        with get_connection(repo_db) as conn:
            record = repo.get_system_metrics_by_id(conn, metric_id)
            assert record is not None
            assert isinstance(record, SystemMetricRecord)
            assert record.id == metric_id
            assert record.cpu_percent == 45.5
            assert record.cpu_logical_cores == 8
            assert record.cpu_physical_cores == 4
            assert record.memory_percent == 50.0
            assert record.disk_percent == 50.0
            assert record.network_bytes_sent_per_sec == 1024.0
            assert record.process_count == 2
            assert record.top_process_pid == 1001
            assert record.top_process_name == "python.exe"
            assert record.top_process_cpu_percent == 25.0
            assert "per_core_percent" in record.raw_payload["cpu"]

    def test_insert_and_retrieve_feature_vector(
        self,
        repo_db: Path,
        sample_feature_vector: FeatureVector,
    ) -> None:
        """Verify inserting FeatureVector stores all 39 features accurately."""
        repo = MetricsRepository()
        with db_session(repo_db) as session:
            vector_id = repo.insert_feature_vector(session, sample_feature_vector)

        assert vector_id > 0

        with get_connection(repo_db) as conn:
            record = repo.get_feature_vector_by_id(conn, vector_id)
            assert record is not None
            assert isinstance(record, FeatureVectorRecord)
            assert record.id == vector_id
            assert len(record.features) == 39
            assert record.features["cpu_utilization_percent"] == 45.5
            assert record.features["network_bytes_recv_per_sec"] == 2048.0
            assert record.metadata["window_size"] == 12

    def test_insert_and_retrieve_validation_log(
        self,
        repo_db: Path,
    ) -> None:
        """Verify inserting and querying validation records and structured issues."""
        repo = MetricsRepository()
        now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
        validation = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    domain="disk",
                    field_name="utilization_percent",
                    issue_type="out_of_range",
                    message="Disk space critical",
                    value=96.5,
                    severity="warning",
                ),
                ValidationIssue(
                    domain="cpu",
                    field_name="utilization_percent",
                    issue_type="non_finite",
                    message="CPU percent is NaN",
                    value="nan",
                    severity="error",
                ),
            ],
        )

        with db_session(repo_db) as session:
            log_id = repo.insert_validation_log(session, validation, now)

        assert log_id > 0

        with get_connection(repo_db) as conn:
            record = repo.get_validation_log_by_id(conn, log_id)
            assert record is not None
            assert isinstance(record, ValidationLogRecord)
            assert record.is_valid is False
            assert record.issues_count == 2
            assert record.has_errors is True
            assert len(record.issues) == 2
            assert record.issues[0]["domain"] == "disk"
            assert record.issues[1]["severity"] == "error"

    def test_time_range_and_latest_queries(
        self,
        repo_db: Path,
        sample_metrics: SystemMetrics,
        sample_feature_vector: FeatureVector,
    ) -> None:
        """Verify range queries filter chronologically and latest queries order by timestamp desc."""
        repo = MetricsRepository()
        t0 = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)

        with db_session(repo_db) as session:
            for i in range(5):
                ts = t0 + timedelta(minutes=i)
                m = SystemMetrics(
                    timestamp=ts,
                    cpu=CPUMetrics(utilization_percent=float(10 * i), logical_cores=4),
                )
                repo.insert_system_metrics(session, m)

        with get_connection(repo_db) as conn:
            # Latest 3
            latest = repo.get_latest_system_metrics(conn, limit=3)
            assert len(latest) == 3
            assert latest[0].cpu_percent == 40.0
            assert latest[1].cpu_percent == 30.0

            # Range: t0 + 1m to t0 + 3m
            start = t0 + timedelta(minutes=1)
            end = t0 + timedelta(minutes=3)
            range_records = repo.get_system_metrics_range(conn, start, end)
            assert len(range_records) == 3
            assert range_records[0].timestamp == start
            assert range_records[-1].timestamp == end

    def test_count_and_retention_deletion(
        self,
        repo_db: Path,
        sample_metrics: SystemMetrics,
        sample_feature_vector: FeatureVector,
    ) -> None:
        """Verify count methods and retention deletion."""
        repo = MetricsRepository()
        t_old = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
        t_new = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

        with db_session(repo_db) as session:
            # Old sample
            old_metrics = SystemMetrics(timestamp=t_old)
            m_old_id = repo.insert_system_metrics(session, old_metrics)
            old_fv = FeatureVector(
                timestamp=t_old,
                features=sample_feature_vector.features,
                metadata=sample_feature_vector.metadata,
            )
            repo.insert_feature_vector(session, old_fv, metric_id=m_old_id)

            # New sample
            new_metrics = SystemMetrics(timestamp=t_new)
            m_new_id = repo.insert_system_metrics(session, new_metrics)
            repo.insert_feature_vector(session, sample_feature_vector, metric_id=m_new_id)

        with get_connection(repo_db) as conn:
            counts = repo.count_all_records(conn)
            assert counts["system_metrics"] == 2
            assert counts["feature_vectors"] == 2

            # Purge records older than mid-September
            cutoff = datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)
            with db_session(repo_db) as session:
                deleted = repo.delete_records_older_than(session, cutoff)

            assert deleted["system_metrics"] == 1
            assert deleted["feature_vectors"] == 1

            new_counts = repo.count_all_records(conn)
            assert new_counts["system_metrics"] == 1
            assert new_counts["feature_vectors"] == 1

    def test_count_records_prevents_sql_injection(self, repo_db: Path) -> None:
        """Verify count_records rejects table names outside the allowed whitelist."""
        repo = MetricsRepository()
        with get_connection(repo_db) as conn:
            with pytest.raises(ValueError, match="Unauthorized table name"):
                repo.count_records(conn, "system_metrics; DROP TABLE system_metrics;--")

    def test_nonexistent_id_returns_none(self, repo_db: Path) -> None:
        """Verify querying non-existent primary keys gracefully returns None."""
        repo = MetricsRepository()
        with get_connection(repo_db) as conn:
            assert repo.get_system_metrics_by_id(conn, 9999) is None
            assert repo.get_feature_vector_by_id(conn, 9999) is None
            assert repo.get_validation_log_by_id(conn, 9999) is None
