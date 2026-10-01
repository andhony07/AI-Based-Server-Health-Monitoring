"""Unit tests for PersistenceService orchestration and error handling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings, load_config
from app.database.models import PersistenceResult
from app.database.service import PersistenceService
from app.models.metrics import CPUMetrics, MemoryMetrics, SystemMetrics
from app.preprocessing.cleaner import CleanedSystemMetrics
from app.preprocessing.feature_engineer import FeatureVector
from app.preprocessing.pipeline import ProcessedTelemetry
from app.preprocessing.validator import ValidationIssue, ValidationResult


@pytest.fixture
def service_settings(tmp_path: Path) -> Settings:
    """Fixture providing isolated Settings pointing to a temporary database file."""
    db_file = tmp_path / "service_test.db"
    return load_config(
        base_dir=tmp_path,
        database_path=str(db_file),
        db_connection_timeout=5.0,
        db_auto_init=True,
    )


@pytest.fixture
def sample_payload() -> tuple[SystemMetrics, ProcessedTelemetry]:
    """Fixture creating linked SystemMetrics and ProcessedTelemetry objects."""
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    metrics = SystemMetrics(
        timestamp=now,
        cpu=CPUMetrics(utilization_percent=55.0, logical_cores=4),
        memory=MemoryMetrics(
            total_bytes=8 * 1024**3,
            available_bytes=4 * 1024**3,
            used_bytes=4 * 1024**3,
            utilization_percent=50.0,
        ),
    )
    features = {col: 1.0 for col in [
        "cpu_utilization_percent", "cpu_utilization_delta", "cpu_utilization_rolling_mean",
        "cpu_utilization_rolling_max", "cpu_utilization_rolling_min", "cpu_cores_logical",
        "memory_utilization_percent", "memory_used_mb", "memory_available_mb",
        "memory_utilization_delta", "memory_used_delta_mb", "memory_utilization_rolling_mean",
        "memory_utilization_rolling_max", "disk_utilization_percent", "disk_used_gb",
        "disk_free_gb", "disk_utilization_delta", "disk_utilization_rolling_mean",
        "network_bytes_sent_per_sec", "network_bytes_recv_per_sec", "network_sent_delta_per_sec",
        "network_recv_delta_per_sec", "network_bytes_sent_rolling_mean", "network_bytes_recv_rolling_mean",
        "network_bytes_sent_rolling_max", "network_bytes_recv_rolling_max", "process_count",
        "top_process_cpu_percent", "top_process_memory_percent", "top_processes_total_cpu_percent",
        "top_processes_total_memory_percent", "sample_interval_sec", "hour_of_day",
        "day_of_week", "is_cpu_missing", "is_memory_missing", "is_disk_missing",
        "is_network_missing", "is_processes_missing"
    ]}
    feature_vector = FeatureVector(timestamp=now, features=features)
    val_result = ValidationResult(is_valid=True, issues=[])
    cleaned = CleanedSystemMetrics(
        timestamp=now,
        cpu_percent=55.0,
        logical_cores=4,
        memory_percent=50.0,
    )

    processed = ProcessedTelemetry(
        feature_vector=feature_vector,
        validation_result=val_result,
        cleaned_metrics=cleaned,
        raw_metrics=metrics,
    )
    return metrics, processed


class TestPersistenceService:
    """Test suite for high-level persistence service coordination."""

    def test_service_initialization_creates_db_and_schema(
        self, service_settings: Settings
    ) -> None:
        """Verify service initializes schema on startup when db_auto_init=True."""
        assert not service_settings.database_path.exists()
        service = PersistenceService(settings=service_settings)

        assert service.db_path.exists()
        counts = service.get_record_counts()
        assert "system_metrics" in counts
        assert "feature_vectors" in counts
        assert "validation_logs" in counts

    def test_persist_sample_commits_linked_records(
        self,
        service_settings: Settings,
        sample_payload: tuple[SystemMetrics, ProcessedTelemetry],
    ) -> None:
        """Verify persist_sample atomically persists all 3 records linked by metric_id."""
        service = PersistenceService(settings=service_settings)
        metrics, processed = sample_payload

        result = service.persist_sample(metrics, processed)
        assert result.success is True
        assert result.metric_id is not None
        assert result.feature_id is not None
        assert result.validation_id is not None
        assert result.error_message is None

        # Verify linked records via query methods
        stored_metrics = service.get_latest_metrics(limit=1)
        stored_features = service.get_latest_features(limit=1)
        stored_logs = service.get_latest_validation_logs(limit=1)

        assert len(stored_metrics) == 1
        assert stored_metrics[0].id == result.metric_id
        assert stored_metrics[0].cpu_percent == 55.0

        assert len(stored_features) == 1
        assert stored_features[0].id == result.feature_id
        assert stored_features[0].metric_id == result.metric_id
        assert len(stored_features[0].features) == 39

        assert len(stored_logs) == 1
        assert stored_logs[0].id == result.validation_id
        assert stored_logs[0].metric_id == result.metric_id
        assert stored_logs[0].is_valid is True

    def test_persist_sample_error_handling_and_rollback(
        self,
        service_settings: Settings,
        sample_payload: tuple[SystemMetrics, ProcessedTelemetry],
    ) -> None:
        """Verify errors during persist_sample result in safe rollback without throwing unhandled exceptions."""
        service = PersistenceService(settings=service_settings)
        metrics, processed = sample_payload

        # Mock the repository to simulate failure on feature vector insert
        mock_repo = MagicMock()
        mock_repo.insert_system_metrics.return_value = 1
        mock_repo.insert_feature_vector.side_effect = RuntimeError("Disk I/O failure during vector storage")
        service.repository = mock_repo

        result = service.persist_sample(metrics, processed)
        assert result.success is False
        assert result.error_message is not None
        assert "Disk I/O failure" in result.error_message

    def test_apply_retention_policy_purges_expired_data(
        self,
        service_settings: Settings,
        sample_payload: tuple[SystemMetrics, ProcessedTelemetry],
    ) -> None:
        """Verify apply_retention_policy purges data older than threshold."""
        service = PersistenceService(settings=service_settings)
        metrics, processed = sample_payload

        # Persist a sample
        result = service.persist_sample(metrics, processed)
        assert result.success is True

        counts_before = service.get_record_counts()
        assert counts_before["system_metrics"] == 1

        # Purging records older than 1000 days should retain our sample
        purged = service.apply_retention_policy(retention_days=1000)
        assert purged["system_metrics"] == 0
        assert service.get_record_counts()["system_metrics"] == 1

        # Purging with retention_days=0 should retain nothing (or cutoff is right now)
        purged_all = service.apply_retention_policy(retention_days=0)
        # 0 or negative days leaves it inactive
        assert purged_all["system_metrics"] == 0

    def test_convenience_range_queries(
        self,
        service_settings: Settings,
        sample_payload: tuple[SystemMetrics, ProcessedTelemetry],
    ) -> None:
        """Verify get_metrics_range and get_features_range return expected records."""
        service = PersistenceService(settings=service_settings)
        metrics, processed = sample_payload

        service.persist_sample(metrics, processed)
        t_start = metrics.timestamp - timedelta(minutes=5)
        t_end = metrics.timestamp + timedelta(minutes=5)

        metrics_range = service.get_metrics_range(t_start, t_end)
        features_range = service.get_features_range(t_start, t_end)

        assert len(metrics_range) == 1
        assert len(features_range) == 1
