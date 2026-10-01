"""Unit and integration tests for DashboardService coordinator."""

from __future__ import annotations

import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings, load_config
from app.dashboard.services.dashboard_service import DashboardService
from app.database.models import (
    FeatureVectorRecord,
    PersistenceResult,
    SystemMetricRecord,
    ValidationLogRecord,
)
from app.database.service import PersistenceService
from app.ml.models import AnomalyResult, HealthScoreResult, PredictionResult, RiskCategory
from app.ml.prediction_service import PredictionService
from app.models.metrics import CPUMetrics, MemoryMetrics, SystemMetrics
from app.preprocessing.feature_engineer import FeatureVector
from app.preprocessing.pipeline import ProcessedTelemetry
from app.preprocessing.validator import ValidationResult


@pytest.fixture
def temp_dashboard_env(tmp_path: Path) -> tuple[Settings, DashboardService]:
    """Create a self-contained temporary environment for DashboardService testing."""
    db_file = tmp_path / "test_dashboard.db"
    settings = load_config(
        database_path=db_file,
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
    )
    settings.ensure_directories()

    persistence = PersistenceService(settings=settings)
    pred_service = PredictionService(settings=settings, auto_load=False)
    service = DashboardService(
        settings=settings,
        persistence_service=persistence,
        prediction_service=pred_service,
    )
    return settings, service


class TestDashboardService:
    """Test suite for DashboardService data coordinator."""

    def test_init_and_empty_database_behavior(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify clean behavior when initialized against an empty database."""
        _, service = temp_dashboard_env

        # Empty database returns None without error
        assert service.get_latest_metrics() is None
        assert service.get_latest_feature_vector() is None
        assert service.get_latest_prediction() is None
        assert service.get_historical_metrics() == []
        assert service.get_historical_features() == []
        assert service.get_historical_anomalies() == []

        # Database summary should report zero counts
        summary = service.get_database_summary()
        assert summary["database_exists"] is True
        assert summary["counts"]["system_metrics"] == 0
        assert summary["counts"]["feature_vectors"] == 0
        assert summary["earliest_timestamp"] is None
        assert summary["latest_timestamp"] is None

    def test_get_latest_data_after_persistence(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify retrieval of latest metrics, features, and predictions after persisting data."""
        _, service = temp_dashboard_env

        now = datetime.now(timezone.utc)
        metrics = SystemMetrics(
            timestamp=now,
            cpu=CPUMetrics(utilization_percent=35.0, logical_cores=8, physical_cores=4),
            memory=MemoryMetrics(total_bytes=16 * 1024**3, available_bytes=8 * 1024**3, used_bytes=8 * 1024**3, utilization_percent=50.0),
            disk=None,
            network=None,
            processes=[],
        )

        feat_vector = FeatureVector(
            features={
                "cpu_utilization_percent": 35.0,
                "memory_utilization_percent": 50.0,
                "disk_utilization_percent": 40.0,
                "is_cpu_missing": 0.0,
                "is_memory_missing": 0.0,
                "is_disk_missing": 1.0,
            },
            timestamp=now,
        )

        processed = ProcessedTelemetry(
            raw_metrics=metrics,
            cleaned_metrics=metrics,  # type: ignore[arg-type]
            validation_result=ValidationResult(is_valid=True),
            feature_vector=feat_vector,
        )

        persist_res = service.persistence.persist_sample(metrics, processed)
        assert persist_res.success is True

        # Now latest metrics and features must be available
        latest_m = service.get_latest_metrics()
        assert latest_m is not None
        assert latest_m.cpu_percent == 35.0
        assert latest_m.memory_percent == 50.0

        latest_f = service.get_latest_feature_vector()
        assert latest_f is not None
        assert latest_f.features["cpu_utilization_percent"] == 35.0

        # Prediction evaluation should succeed in heuristic fallback mode
        pred = service.get_latest_prediction()
        assert pred is not None
        assert 0.0 <= pred.health_score <= 100.0
        assert pred.risk_category in list(RiskCategory)

    def test_get_historical_metrics_filtering(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify historical metric time-range filtering and limit truncation."""
        _, service = temp_dashboard_env

        base_time = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
        for i in range(5):
            t = base_time + timedelta(minutes=i * 10)
            m = SystemMetrics(
                timestamp=t,
                cpu=CPUMetrics(utilization_percent=20.0 + i, logical_cores=4, physical_cores=2),
                memory=None,
                disk=None,
                network=None,
                processes=[],
            )
            fv = FeatureVector(features={"cpu_utilization_percent": 20.0 + i}, timestamp=t)
            proc = ProcessedTelemetry(
                raw_metrics=m,
                cleaned_metrics=m,  # type: ignore[arg-type]
                validation_result=ValidationResult(is_valid=True),
                feature_vector=fv,
            )
            service.persistence.persist_sample(m, proc)

        # All 5 records
        all_records = service.get_historical_metrics(limit=10)
        assert len(all_records) == 5

        # Limit to 3
        limited = service.get_historical_metrics(limit=3)
        assert len(limited) == 3

        # Range filter
        range_records = service.get_historical_metrics(
            start_time=base_time + timedelta(minutes=10),
            end_time=base_time + timedelta(minutes=30),
        )
        assert len(range_records) == 3

    def test_get_historical_anomalies_evaluation(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify correlation of historical feature vectors with prediction evaluation."""
        _, service = temp_dashboard_env

        t = datetime.now(timezone.utc)
        m = SystemMetrics(
            timestamp=t,
            cpu=CPUMetrics(utilization_percent=96.0, logical_cores=4, physical_cores=2),
            memory=MemoryMetrics(total_bytes=1000, available_bytes=10, used_bytes=990, utilization_percent=99.0),
            disk=None,
            network=None,
            processes=[],
        )
        fv = FeatureVector(
            features={"cpu_utilization_percent": 96.0, "memory_utilization_percent": 99.0},
            timestamp=t,
        )
        proc = ProcessedTelemetry(
            raw_metrics=m,
            cleaned_metrics=m,  # type: ignore[arg-type]
            validation_result=ValidationResult(is_valid=True),
            feature_vector=fv,
        )
        service.persistence.persist_sample(m, proc)

        anomalies = service.get_historical_anomalies(limit=10)
        assert len(anomalies) == 1
        anom = anomalies[0]
        assert anom["risk_category"] == "Critical"  # Critical override for 96% CPU and 99% RAM
        assert anom["cpu_percent"] == 96.0
        assert anom["memory_percent"] == 99.0
        assert "health_score" in anom
        assert "anomaly_score" in anom

    def test_capture_live_snapshot(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify on-demand live telemetry snapshot capture."""
        _, service = temp_dashboard_env

        mock_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=25.0, logical_cores=8, physical_cores=4),
            memory=MemoryMetrics(total_bytes=8000, available_bytes=4000, used_bytes=4000, utilization_percent=50.0),
            disk=None,
            network=None,
            processes=[],
        )
        service.collector.collect = MagicMock(return_value=mock_metrics)

        record, prediction, err = service.capture_live_snapshot(persist=True)
        assert err is None
        assert record is not None
        assert record.cpu_percent == 25.0
        assert prediction is not None
        assert prediction.risk_category in list(RiskCategory)

    def test_background_monitoring_lifecycle(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify starting, status inspection, double-start rejection, and stopping worker."""
        _, service = temp_dashboard_env

        # Mock collector to avoid heavy hardware polling in test
        mock_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=15.0, logical_cores=4, physical_cores=2),
            memory=None,
            disk=None,
            network=None,
            processes=[],
        )
        service.collector.collect = MagicMock(return_value=mock_metrics)

        assert service.is_background_monitoring_running() is False

        # Start background worker
        started = service.start_background_monitoring(interval=0.1)
        assert started is True
        assert service.is_background_monitoring_running() is True

        # Second start attempt must return False
        assert service.start_background_monitoring(interval=0.1) is False

        # Let worker run for a brief interval
        time.sleep(0.3)

        # Stop worker
        stopped = service.stop_background_monitoring(timeout=2.0)
        assert stopped is True
        assert service.is_background_monitoring_running() is False

    def test_database_summary_reporting(
        self,
        temp_dashboard_env: tuple[Settings, DashboardService],
    ) -> None:
        """Verify database summary metrics reporting with valid timestamps."""
        _, service = temp_dashboard_env

        t1 = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

        for t in (t1, t2):
            m = SystemMetrics(timestamp=t, cpu=None, memory=None, disk=None, network=None, processes=[])
            fv = FeatureVector(features={}, timestamp=t)
            p = ProcessedTelemetry(raw_metrics=m, cleaned_metrics=m, validation_result=ValidationResult(is_valid=True), feature_vector=fv)  # type: ignore[arg-type]
            service.persistence.persist_sample(m, p)

        summary = service.get_database_summary()
        assert summary["counts"]["system_metrics"] == 2
        assert summary["total_records"] >= 2
        assert summary["earliest_timestamp"] == t1
        assert summary["latest_timestamp"] == t2
