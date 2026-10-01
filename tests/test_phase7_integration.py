"""Phase 7 — End-to-end integration, reliability, and edge-case tests.

Validates the complete data pipeline:
    System Metrics → Preprocessing → Feature Engineering → SQLite →
    ML Analysis → Health/Risk Assessment → Dashboard Service

All tests use isolated temporary databases and do not modify the user's
production database or saved model artifacts.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.collectors.system_collector import SystemCollector
from app.core.config import Settings, load_config
from app.dashboard.services.dashboard_service import DashboardService
from app.database.connection import (
    DatabaseConnectionError,
    DatabaseTransactionError,
    create_connection,
    db_session,
    get_connection,
    transaction_scope,
)
from app.database.migrations import apply_migrations, get_current_schema_version
from app.database.models import (
    FeatureVectorRecord,
    PersistenceResult,
    SystemMetricRecord,
    ValidationLogRecord,
    parse_utc_timestamp,
)
from app.database.repository import MetricsRepository
from app.database.schema import FEATURE_COLUMNS, SCHEMA_VERSION
from app.database.service import PersistenceService
from app.ml.anomaly_detector import IsolationForestDetector, NotFittedError
from app.ml.feature_schema import (
    EXPECTED_FEATURE_NAMES,
    FEATURE_DIMENSION,
    feature_dict_to_array,
    validate_feature_mapping,
    validate_feature_vector_finite,
)
from app.ml.health_score import HealthScoreCalculator
from app.ml.model_manager import (
    IncompatibleModelError,
    ModelManager,
    ModelNotFoundError,
)
from app.ml.models import (
    AnomalyResult,
    HealthScoreResult,
    ModelMetadata,
    PredictionResult,
    RiskCategory,
)
from app.ml.prediction_service import PredictionService
from app.ml.risk_analyzer import RiskAnalyzer
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.preprocessing.cleaner import MetricsCleaner
from app.preprocessing.feature_engineer import FeatureEngineer, FeatureVector
from app.preprocessing.pipeline import PreprocessingPipeline, ProcessedTelemetry
from app.preprocessing.validator import MetricsValidator, ValidationResult


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_settings(tmp_path: Path) -> Settings:
    """Create an isolated Settings object pointing to a temporary directory."""
    return load_config(
        database_path=tmp_path / "test.db",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
        metric_collection_interval="1.0",
    )


def _make_realistic_metrics(
    timestamp: Optional[datetime] = None,
    cpu_pct: float = 35.0,
    mem_pct: float = 55.0,
    disk_pct: float = 42.0,
) -> SystemMetrics:
    """Construct a realistic synthetic SystemMetrics snapshot for testing."""
    ts = timestamp or datetime.now(timezone.utc)
    return SystemMetrics(
        timestamp=ts,
        cpu=CPUMetrics(
            utilization_percent=cpu_pct,
            logical_cores=8,
            physical_cores=4,
            per_core_percent=[cpu_pct + i for i in range(8)],
        ),
        memory=MemoryMetrics(
            total_bytes=16 * 1024**3,
            available_bytes=int(16 * 1024**3 * (1 - mem_pct / 100)),
            used_bytes=int(16 * 1024**3 * (mem_pct / 100)),
            utilization_percent=mem_pct,
        ),
        disk=DiskMetrics(
            partitions=[
                DiskPartitionMetrics(
                    mount_point="C:\\",
                    total_bytes=500 * 1024**3,
                    used_bytes=int(500 * 1024**3 * (disk_pct / 100)),
                    free_bytes=int(500 * 1024**3 * (1 - disk_pct / 100)),
                    utilization_percent=disk_pct,
                    device="C:\\",
                    fstype="NTFS",
                ),
            ],
            total_bytes=500 * 1024**3,
            used_bytes=int(500 * 1024**3 * (disk_pct / 100)),
            free_bytes=int(500 * 1024**3 * (1 - disk_pct / 100)),
            utilization_percent=disk_pct,
        ),
        network=NetworkMetrics(
            bytes_sent=1_000_000,
            bytes_recv=2_000_000,
            packets_sent=500,
            packets_recv=800,
            bytes_sent_per_sec=5000.0,
            bytes_recv_per_sec=12000.0,
        ),
        processes=[
            ProcessMetrics(pid=1000, name="python.exe", cpu_percent=12.0, memory_percent=3.5, status="running"),
            ProcessMetrics(pid=1001, name="chrome.exe", cpu_percent=8.5, memory_percent=5.2, status="running"),
        ],
    )


def _make_full_feature_dict(
    cpu_pct: float = 35.0,
    mem_pct: float = 55.0,
    disk_pct: float = 42.0,
) -> dict[str, float]:
    """Build a complete 39-feature dictionary with plausible values."""
    return {
        "cpu_utilization_percent": cpu_pct,
        "cpu_utilization_delta": 0.5,
        "cpu_utilization_rolling_mean": cpu_pct - 1.0,
        "cpu_utilization_rolling_max": cpu_pct + 2.0,
        "cpu_utilization_rolling_min": cpu_pct - 3.0,
        "cpu_cores_logical": 8.0,
        "memory_utilization_percent": mem_pct,
        "memory_used_mb": mem_pct * 160.0,
        "memory_available_mb": (100 - mem_pct) * 160.0,
        "memory_utilization_delta": 0.2,
        "memory_used_delta_mb": 10.0,
        "memory_utilization_rolling_mean": mem_pct - 0.5,
        "memory_utilization_rolling_max": mem_pct + 1.0,
        "disk_utilization_percent": disk_pct,
        "disk_used_gb": disk_pct * 5.0,
        "disk_free_gb": (100 - disk_pct) * 5.0,
        "disk_utilization_delta": 0.0,
        "disk_utilization_rolling_mean": disk_pct,
        "network_bytes_sent_per_sec": 5000.0,
        "network_bytes_recv_per_sec": 12000.0,
        "network_sent_delta_per_sec": 100.0,
        "network_recv_delta_per_sec": 200.0,
        "network_bytes_sent_rolling_mean": 4800.0,
        "network_bytes_recv_rolling_mean": 11500.0,
        "network_bytes_sent_rolling_max": 6000.0,
        "network_bytes_recv_rolling_max": 14000.0,
        "process_count": 2.0,
        "top_process_cpu_percent": 12.0,
        "top_process_memory_percent": 5.2,
        "top_processes_total_cpu_percent": 20.5,
        "top_processes_total_memory_percent": 8.7,
        "sample_interval_sec": 5.0,
        "hour_of_day": 14.0,
        "day_of_week": 3.0,
        "is_cpu_missing": 0.0,
        "is_memory_missing": 0.0,
        "is_disk_missing": 0.0,
        "is_network_missing": 0.0,
        "is_processes_missing": 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Section 1: End-to-End Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEndToEndDataFlow:
    """Validates complete data pipeline: collection → preprocessing → DB → ML → dashboard."""

    def test_live_collection_through_full_pipeline(self, tmp_path: Path) -> None:
        """Collect real system metrics and process through entire pipeline."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        collector = SystemCollector(settings=settings)
        pipeline = PreprocessingPipeline(settings=settings)
        db_service = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)

        # Step 1: Collect real metrics
        metrics = collector.collect()
        assert isinstance(metrics, SystemMetrics)
        assert metrics.timestamp.tzinfo is not None

        # Step 2: Preprocess and extract features
        processed = pipeline.process(metrics)
        assert isinstance(processed, ProcessedTelemetry)
        assert len(processed.feature_vector.features) == FEATURE_DIMENSION

        # Step 3: Persist to SQLite
        result = db_service.persist_sample(metrics, processed)
        assert result.success is True
        assert result.metric_id is not None
        assert result.feature_id is not None
        assert result.validation_id is not None

        # Step 4: Retrieve and verify persisted data
        latest_metrics = db_service.get_latest_metrics(limit=1)
        assert len(latest_metrics) == 1
        assert latest_metrics[0].id == result.metric_id

        latest_features = db_service.get_latest_features(limit=1)
        assert len(latest_features) == 1
        assert latest_features[0].id == result.feature_id
        assert len(latest_features[0].features) == FEATURE_DIMENSION

        latest_logs = db_service.get_latest_validation_logs(limit=1)
        assert len(latest_logs) == 1
        assert latest_logs[0].id == result.validation_id

        # Step 5: Run ML prediction (heuristic fallback – no trained model)
        prediction = pred_service.predict(processed)
        assert isinstance(prediction, PredictionResult)
        assert prediction.risk_category in list(RiskCategory)
        assert 0.0 <= prediction.health_score <= 100.0
        assert len(prediction.warnings) > 0  # Should warn about no model

        # Step 6: Record counts match
        counts = db_service.get_record_counts()
        assert counts["system_metrics"] == 1
        assert counts["feature_vectors"] == 1
        assert counts["validation_logs"] == 1

        db_service.close()

    def test_feature_vector_is_39_dimensions_from_live_data(self, tmp_path: Path) -> None:
        """Verify live collection produces the expected 39-feature vector schema."""
        settings = _make_settings(tmp_path)
        collector = SystemCollector(settings=settings)
        pipeline = PreprocessingPipeline(settings=settings)

        metrics = collector.collect()
        processed = pipeline.process(metrics)

        features = processed.feature_vector.features
        assert len(features) == FEATURE_DIMENSION

        # Every expected feature name must be present
        for name in EXPECTED_FEATURE_NAMES:
            assert name in features, f"Missing feature: {name}"
            assert isinstance(features[name], (int, float)), f"Non-numeric feature: {name}"

        # Feature vector must be convertible to numpy array
        X = feature_dict_to_array(features)
        assert X.shape == (1, FEATURE_DIMENSION)
        assert np.all(np.isfinite(X))

    def test_multiple_samples_accumulate_correctly(self, tmp_path: Path) -> None:
        """Verify that multiple collection-persist cycles create consistent records."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        pipeline = PreprocessingPipeline(settings=settings)
        db_service = PersistenceService(settings=settings)

        num_samples = 5
        for i in range(num_samples):
            metrics = _make_realistic_metrics(
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
                cpu_pct=20.0 + i * 5,
            )
            processed = pipeline.process(metrics)
            result = db_service.persist_sample(metrics, processed)
            assert result.success is True

        counts = db_service.get_record_counts()
        assert counts["system_metrics"] == num_samples
        assert counts["feature_vectors"] == num_samples
        assert counts["validation_logs"] == num_samples

        # Foreign key consistency
        features = db_service.get_latest_features(limit=num_samples)
        for feat in features:
            assert feat.metric_id is not None
            assert feat.metric_id > 0

        db_service.close()

    def test_dashboard_service_full_cycle(self, tmp_path: Path) -> None:
        """Validate dashboard service retrieval after collection and persistence."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        persistence = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)
        pipeline = PreprocessingPipeline(settings=settings)

        dash = DashboardService(
            settings=settings,
            persistence_service=persistence,
            prediction_service=pred_service,
            pipeline=pipeline,
        )

        # Persist a sample
        metrics = _make_realistic_metrics()
        processed = pipeline.process(metrics)
        persistence.persist_sample(metrics, processed)

        # Dashboard should retrieve it
        latest = dash.get_latest_metrics()
        assert latest is not None

        latest_feat = dash.get_latest_feature_vector()
        assert latest_feat is not None

        pred = dash.get_latest_prediction()
        assert pred is not None
        assert pred.risk_category in list(RiskCategory)

        # Database summary should be populated
        summary = dash.get_database_summary()
        assert summary["counts"]["system_metrics"] == 1
        assert summary["database_exists"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Section 2: Reliability and Edge-Case Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCasesAndReliability:
    """Tests for graceful degradation under adverse conditions."""

    def test_empty_database_no_crash(self, tmp_path: Path) -> None:
        """All services return safe defaults on empty database."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        persistence = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)
        dash = DashboardService(
            settings=settings,
            persistence_service=persistence,
            prediction_service=pred_service,
        )

        assert dash.get_latest_metrics() is None
        assert dash.get_latest_feature_vector() is None
        assert dash.get_latest_prediction() is None
        assert dash.get_historical_metrics() == []
        assert dash.get_historical_features() == []
        assert dash.get_historical_anomalies() == []
        assert dash.get_recent_validation_logs() == []

        summary = dash.get_database_summary()
        assert summary["counts"]["system_metrics"] == 0
        assert summary["earliest_timestamp"] is None

    def test_prediction_without_trained_model(self, tmp_path: Path) -> None:
        """Prediction service gracefully falls back to heuristics without a model."""
        settings = _make_settings(tmp_path)
        pred_service = PredictionService(settings=settings, auto_load=False)

        assert pred_service.is_model_loaded is False

        features = _make_full_feature_dict()
        result = pred_service.predict(features)

        assert isinstance(result, PredictionResult)
        assert result.is_anomaly is False
        assert result.anomaly_score == 0.0
        assert result.health_score is not None
        assert 0.0 <= result.health_score <= 100.0
        assert result.risk_category in list(RiskCategory)
        assert any("heuristic" in w.lower() or "no trained" in w.lower() for w in result.warnings)

    def test_missing_model_file_graceful(self, tmp_path: Path) -> None:
        """PredictionService handles missing model file without crashing."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        pred_service = PredictionService(settings=settings, auto_load=True)
        assert pred_service.is_model_loaded is False
        assert pred_service.model_name == "HeuristicBaseline"

    def test_corrupted_model_metadata_graceful(self, tmp_path: Path) -> None:
        """ModelManager handles corrupted metadata without crashing."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        models_dir = settings.models_dir

        # Write a valid joblib but corrupted metadata
        import joblib
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(n_estimators=10, random_state=42)
        model.fit(np.random.randn(50, FEATURE_DIMENSION))
        joblib.dump(model, models_dir / "isolation_forest.joblib", compress=3)

        corrupt_meta = models_dir / "isolation_forest_metadata.json"
        corrupt_meta.write_text("NOT VALID JSON {{{", encoding="utf-8")

        manager = ModelManager(settings=settings)
        with pytest.raises(IncompatibleModelError):
            manager.load_model("isolation_forest")

    def test_incompatible_feature_schema_model(self, tmp_path: Path) -> None:
        """Model with wrong feature count is rejected."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        models_dir = settings.models_dir

        import joblib
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(n_estimators=10, random_state=42)
        model.fit(np.random.randn(20, 10))  # Wrong dimension
        joblib.dump(model, models_dir / "bad_model.joblib")

        bad_meta = {
            "model_name": "BadModel",
            "model_type": "IsolationForest",
            "version": "1.0.0",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_samples_count": 20,
            "feature_names": [f"feat_{i}" for i in range(10)],  # Wrong count
        }
        (models_dir / "bad_model_metadata.json").write_text(
            json.dumps(bad_meta), encoding="utf-8"
        )

        manager = ModelManager(settings=settings)
        with pytest.raises(IncompatibleModelError):
            manager.load_model("bad_model")

    def test_metrics_with_missing_subsystems(self, tmp_path: Path) -> None:
        """Pipeline handles metrics with all optional domains set to None."""
        settings = _make_settings(tmp_path)
        pipeline = PreprocessingPipeline(settings=settings)

        empty_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=None,
            memory=None,
            disk=None,
            network=None,
            processes=[],
        )

        processed = pipeline.process(empty_metrics)
        assert processed.feature_vector is not None
        assert len(processed.feature_vector.features) == FEATURE_DIMENSION

        # Missing indicators should be set for None domains
        assert processed.feature_vector.features.get("is_cpu_missing", 0) == 1.0
        assert processed.feature_vector.features.get("is_memory_missing", 0) == 1.0
        assert processed.feature_vector.features.get("is_disk_missing", 0) == 1.0
        assert processed.feature_vector.features.get("is_network_missing", 0) == 1.0
        # processes=[] (empty list, not None) => is_processes_missing == 0.0
        assert processed.feature_vector.features.get("is_processes_missing", 0) == 0.0

    def test_prediction_with_non_finite_features(self, tmp_path: Path) -> None:
        """Prediction handles NaN/Inf values in features without crashing."""
        settings = _make_settings(tmp_path)
        pred_service = PredictionService(settings=settings, auto_load=False)

        features = _make_full_feature_dict()
        features["cpu_utilization_percent"] = float("nan")
        features["memory_utilization_percent"] = float("inf")

        result = pred_service.predict(features)
        assert isinstance(result, PredictionResult)
        # Should warn about non-finite values
        assert any("non-finite" in w.lower() or "Non-finite" in w for w in result.warnings)

    def test_stale_timestamp_ordering(self, tmp_path: Path) -> None:
        """Verify persistence handles out-of-order timestamps."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        pipeline = PreprocessingPipeline(settings=settings)
        db_service = PersistenceService(settings=settings)

        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Insert in reverse chronological order
        for i in [4, 2, 0, 3, 1]:
            ts = base + timedelta(minutes=i)
            metrics = _make_realistic_metrics(timestamp=ts)
            processed = pipeline.process(metrics)
            res = db_service.persist_sample(metrics, processed)
            assert res.success

        # Retrieve should return all 5
        records = db_service.get_latest_metrics(limit=10)
        assert len(records) == 5

        db_service.close()


# ─────────────────────────────────────────────────────────────────────────────
# Section 3: Database Integrity and Performance Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDatabaseIntegrity:
    """SQLite database integrity and transaction tests."""

    def test_sqlite_integrity_check(self, tmp_path: Path) -> None:
        """Verify SQLite PRAGMA integrity_check passes after operations."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        db_service = PersistenceService(settings=settings)
        pipeline = PreprocessingPipeline(settings=settings)

        # Persist several samples
        for i in range(10):
            metrics = _make_realistic_metrics(
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            )
            processed = pipeline.process(metrics)
            db_service.persist_sample(metrics, processed)

        # Run integrity check
        with get_connection(settings.database_path) as conn:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            assert result[0] == "ok", f"Integrity check failed: {result[0]}"

        db_service.close()

    def test_foreign_key_consistency(self, tmp_path: Path) -> None:
        """Verify no orphaned feature_vectors or validation_logs exist."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        db_service = PersistenceService(settings=settings)
        pipeline = PreprocessingPipeline(settings=settings)

        for i in range(5):
            metrics = _make_realistic_metrics(
                timestamp=datetime.now(timezone.utc) + timedelta(seconds=i),
            )
            processed = pipeline.process(metrics)
            db_service.persist_sample(metrics, processed)

        with get_connection(settings.database_path) as conn:
            # Check for foreign key violations
            cursor = conn.execute("PRAGMA foreign_key_check;")
            violations = cursor.fetchall()
            assert len(violations) == 0, f"FK violations found: {violations}"

            # Verify feature_vectors reference valid metric_ids
            cursor = conn.execute("""
                SELECT fv.id, fv.metric_id FROM feature_vectors fv
                WHERE fv.metric_id IS NOT NULL
                AND fv.metric_id NOT IN (SELECT id FROM system_metrics);
            """)
            orphans = cursor.fetchall()
            assert len(orphans) == 0, f"Orphaned feature vectors: {orphans}"

            # Verify validation_logs reference valid metric_ids
            cursor = conn.execute("""
                SELECT vl.id, vl.metric_id FROM validation_logs vl
                WHERE vl.metric_id IS NOT NULL
                AND vl.metric_id NOT IN (SELECT id FROM system_metrics);
            """)
            orphan_logs = cursor.fetchall()
            assert len(orphan_logs) == 0, f"Orphaned validation logs: {orphan_logs}"

        db_service.close()

    def test_transaction_rollback_on_error(self, tmp_path: Path) -> None:
        """Verify that failed transactions are rolled back atomically."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        db_path = settings.database_path
        with get_connection(db_path) as conn:
            apply_migrations(conn)

        # Attempt a transaction that will fail mid-way
        with get_connection(db_path) as conn:
            initial_count = conn.execute(
                "SELECT COUNT(*) as total FROM system_metrics;"
            ).fetchone()[0]

        # Using db_session, simulate a failure after partial insert
        try:
            with db_session(db_path) as session:
                session.execute(
                    "INSERT INTO system_metrics (timestamp, raw_payload_json) VALUES (?, ?);",
                    (datetime.now(timezone.utc).isoformat(), "{}"),
                )
                # Force an error
                raise RuntimeError("Simulated failure")
        except (DatabaseTransactionError, RuntimeError):
            pass

        # Count should remain unchanged
        with get_connection(db_path) as conn:
            after_count = conn.execute(
                "SELECT COUNT(*) as total FROM system_metrics;"
            ).fetchone()[0]

        assert after_count == initial_count, "Transaction was not rolled back"

    def test_retention_purge(self, tmp_path: Path) -> None:
        """Verify retention policy correctly removes old records."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        pipeline = PreprocessingPipeline(settings=settings)
        db_service = PersistenceService(settings=settings)

        old_time = datetime.now(timezone.utc) - timedelta(days=60)
        recent_time = datetime.now(timezone.utc)

        # Insert old record
        old_metrics = _make_realistic_metrics(timestamp=old_time)
        old_processed = pipeline.process(old_metrics)
        db_service.persist_sample(old_metrics, old_processed)

        # Insert recent record
        recent_metrics = _make_realistic_metrics(timestamp=recent_time)
        recent_processed = pipeline.process(recent_metrics)
        db_service.persist_sample(recent_metrics, recent_processed)

        counts_before = db_service.get_record_counts()
        assert counts_before["system_metrics"] == 2

        # Apply 30-day retention
        deleted = db_service.apply_retention_policy(retention_days=30)
        assert deleted["system_metrics"] >= 1

        counts_after = db_service.get_record_counts()
        assert counts_after["system_metrics"] == 1  # Only recent remains

        db_service.close()

    def test_schema_migration_idempotency(self, tmp_path: Path) -> None:
        """Verify running apply_migrations twice is safe and idempotent."""
        db_path = tmp_path / "migration_test.db"
        with get_connection(db_path) as conn:
            v1 = apply_migrations(conn)
            assert v1 == SCHEMA_VERSION

        # Run again — should be a no-op
        with get_connection(db_path) as conn:
            v2 = apply_migrations(conn)
            assert v2 == SCHEMA_VERSION

        # Verify tables exist
        with get_connection(db_path) as conn:
            tables_cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            )
            tables = {row[0] for row in tables_cursor.fetchall()}
            expected = {"system_metrics", "feature_vectors", "validation_logs", "schema_migrations"}
            assert expected.issubset(tables)


# ─────────────────────────────────────────────────────────────────────────────
# Section 4: ML Validation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMLValidation:
    """Validates ML pipeline: feature schema, model lifecycle, scoring, and risk."""

    def test_feature_schema_has_39_features(self) -> None:
        """Verify the canonical feature schema defines exactly 39 features."""
        assert FEATURE_DIMENSION == 39
        assert len(EXPECTED_FEATURE_NAMES) == 39
        assert len(FEATURE_COLUMNS) == 39
        # Schema sources must agree
        assert list(FEATURE_COLUMNS) == EXPECTED_FEATURE_NAMES

    def test_feature_validation_complete_dict(self) -> None:
        """A complete feature dict passes validation."""
        features = _make_full_feature_dict()
        is_valid, errors = validate_feature_mapping(features)
        assert is_valid is True
        assert errors == []

    def test_feature_validation_missing_features(self) -> None:
        """A feature dict missing keys fails validation."""
        features = {"cpu_utilization_percent": 50.0}
        is_valid, errors = validate_feature_mapping(features)
        assert is_valid is False
        assert len(errors) > 0

    def test_anomaly_detector_fit_and_score(self, tmp_path: Path) -> None:
        """IsolationForestDetector fit and score_sample lifecycle."""
        detector = IsolationForestDetector(
            n_estimators=20,
            contamination=0.1,
            random_state=42,
        )
        assert detector.is_fitted is False

        # Train with synthetic data
        X_train = np.random.randn(50, FEATURE_DIMENSION)
        detector.fit(X_train)
        assert detector.is_fitted is True

        # Score a single sample
        X_test = np.random.randn(1, FEATURE_DIMENSION)
        result = detector.score_sample(X_test)
        assert isinstance(result, AnomalyResult)
        assert isinstance(result.is_anomaly, bool)
        assert 0.0 <= result.normalized_score <= 1.0

    def test_anomaly_detector_unfitted_raises(self) -> None:
        """Scoring on unfitted detector raises NotFittedError."""
        detector = IsolationForestDetector()
        X_test = np.random.randn(1, FEATURE_DIMENSION)
        with pytest.raises(NotFittedError):
            detector.score_sample(X_test)

    def test_health_score_ranges(self) -> None:
        """Health score stays within [0, 100] under various inputs."""
        calc = HealthScoreCalculator()

        # Optimal: no anomaly, low resources
        result = calc.calculate(anomaly_score=0.0, cpu_percent=20.0, memory_percent=30.0, disk_percent=40.0)
        assert result.score is not None
        assert 85.0 <= result.score <= 100.0
        assert result.status == "Optimal"

        # Extreme stress
        result = calc.calculate(anomaly_score=1.0, cpu_percent=100.0, memory_percent=100.0, disk_percent=100.0)
        assert result.score is not None
        assert result.score == 0.0
        assert result.status == "Critical"

    def test_risk_category_thresholds(self) -> None:
        """Risk analyzer correctly categorizes at boundary values."""
        analyzer = RiskAnalyzer(
            threshold_low=0.35,
            threshold_moderate=0.55,
            threshold_high=0.75,
            threshold_critical=0.90,
        )

        assert analyzer.evaluate_risk(anomaly_score=0.0) == RiskCategory.NORMAL
        assert analyzer.evaluate_risk(anomaly_score=0.36) == RiskCategory.LOW
        assert analyzer.evaluate_risk(anomaly_score=0.56) == RiskCategory.MODERATE
        assert analyzer.evaluate_risk(anomaly_score=0.76) == RiskCategory.HIGH
        assert analyzer.evaluate_risk(anomaly_score=0.91) == RiskCategory.CRITICAL

    def test_risk_critical_override_on_hardware_saturation(self) -> None:
        """Critical risk triggered by extreme resource saturation regardless of anomaly score."""
        analyzer = RiskAnalyzer()
        result = analyzer.evaluate_risk(
            anomaly_score=0.0,
            cpu_percent=96.0,
            memory_percent=50.0,
            disk_percent=50.0,
        )
        assert result == RiskCategory.CRITICAL

    def test_model_save_load_roundtrip(self, tmp_path: Path) -> None:
        """Model save and load preserves integrity and metadata."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        manager = ModelManager(settings=settings)

        from sklearn.ensemble import IsolationForest
        model = IsolationForest(n_estimators=20, random_state=42)
        X = np.random.randn(30, FEATURE_DIMENSION)
        model.fit(X)

        metadata = ModelMetadata(
            model_name="TestModel",
            model_type="IsolationForest",
            version="1.0.0",
            trained_at=datetime.now(timezone.utc).isoformat(),
            training_samples_count=30,
            feature_names=list(EXPECTED_FEATURE_NAMES),
            hyperparameters={"n_estimators": 20, "contamination": 0.05, "random_state": 42},
        )

        # save_model uses the prefix param for filenames (default "isolation_forest")
        model_path, meta_path = manager.save_model(model, metadata, prefix="test_model")
        assert model_path.exists()
        assert meta_path.exists()

        loaded_model, loaded_meta = manager.load_model("test_model")
        assert loaded_meta.model_name == "TestModel"
        assert loaded_meta.training_samples_count == 30
        assert loaded_meta.feature_names == list(EXPECTED_FEATURE_NAMES)

        # Loaded model should produce same predictions
        pred_original = model.predict(X[:1])
        pred_loaded = loaded_model.predict(X[:1])
        assert np.array_equal(pred_original, pred_loaded)

    def test_prediction_service_with_trained_model(self, tmp_path: Path) -> None:
        """PredictionService produces ML-backed results when model is available."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        manager = ModelManager(settings=settings)

        from sklearn.ensemble import IsolationForest
        model = IsolationForest(n_estimators=20, contamination=0.05, random_state=42)
        X = np.random.randn(50, FEATURE_DIMENSION)
        model.fit(X)

        metadata = ModelMetadata(
            model_name="IsolationForestDetector",
            model_type="IsolationForest",
            version="1.0.0",
            trained_at=datetime.now(timezone.utc).isoformat(),
            training_samples_count=50,
            feature_names=list(EXPECTED_FEATURE_NAMES),
            hyperparameters={"n_estimators": 20, "contamination": 0.05, "random_state": 42},
        )
        manager.save_model(model, metadata)

        pred_service = PredictionService(settings=settings, auto_load=True)
        assert pred_service.is_model_loaded is True

        features = _make_full_feature_dict()
        result = pred_service.predict(features)
        assert isinstance(result, PredictionResult)
        assert result.model_name == "IsolationForestDetector"
        assert result.health_score is not None


# ─────────────────────────────────────────────────────────────────────────────
# Section 5: Dashboard Service Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboardEdgeCases:
    """Tests for dashboard service under adverse conditions."""

    def test_monitoring_start_stop_lifecycle(self, tmp_path: Path) -> None:
        """Background monitoring starts, rejects double start, and stops cleanly."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        persistence = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)
        dash = DashboardService(
            settings=settings,
            persistence_service=persistence,
            prediction_service=pred_service,
        )

        # Mock collector to avoid real hardware polling
        mock_metrics = _make_realistic_metrics()
        dash.collector.collect = MagicMock(return_value=mock_metrics)

        assert dash.is_background_monitoring_running() is False

        # Start
        assert dash.start_background_monitoring(interval=0.1) is True
        assert dash.is_background_monitoring_running() is True

        # Double start rejected
        assert dash.start_background_monitoring(interval=0.1) is False

        time.sleep(0.3)

        # Stop
        assert dash.stop_background_monitoring(timeout=3.0) is True
        assert dash.is_background_monitoring_running() is False

    def test_live_snapshot_persist_and_predict(self, tmp_path: Path) -> None:
        """capture_live_snapshot collects, persists, and predicts without errors."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()

        persistence = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)
        pipeline = PreprocessingPipeline(settings=settings)
        dash = DashboardService(
            settings=settings,
            persistence_service=persistence,
            prediction_service=pred_service,
            pipeline=pipeline,
        )

        mock_metrics = _make_realistic_metrics()
        dash.collector.collect = MagicMock(return_value=mock_metrics)

        record, prediction, err = dash.capture_live_snapshot(persist=True)
        assert err is None
        assert record is not None
        assert prediction is not None
        assert prediction.risk_category in list(RiskCategory)

    def test_historical_anomalies_with_no_data(self, tmp_path: Path) -> None:
        """Historical anomaly evaluation returns empty list on empty database."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        persistence = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)
        dash = DashboardService(
            settings=settings,
            persistence_service=persistence,
            prediction_service=pred_service,
        )
        assert dash.get_historical_anomalies() == []

    def test_database_summary_file_size(self, tmp_path: Path) -> None:
        """Database summary reports correct file size."""
        settings = _make_settings(tmp_path)
        settings.ensure_directories()
        persistence = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings, auto_load=False)
        dash = DashboardService(
            settings=settings,
            persistence_service=persistence,
            prediction_service=pred_service,
        )

        summary = dash.get_database_summary()
        assert summary["database_exists"] is True
        assert summary["file_size_bytes"] > 0
        assert summary["database_path"] == str(settings.database_path)


# ─────────────────────────────────────────────────────────────────────────────
# Section 6: Preprocessing Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

class TestPreprocessingEdgeCases:
    """Validates preprocessing under partial failures and missing data."""

    def test_partial_collector_failure_produces_valid_features(self, tmp_path: Path) -> None:
        """Even with some collectors failing, pipeline produces 39 features."""
        settings = _make_settings(tmp_path)
        pipeline = PreprocessingPipeline(settings=settings)

        # Only CPU available
        partial_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=45.0, logical_cores=4, physical_cores=2),
            memory=None,
            disk=None,
            network=None,
            processes=[],
            errors=["Memory collection error: simulated", "Disk collection error: simulated"],
        )

        processed = pipeline.process(partial_metrics)
        assert len(processed.feature_vector.features) == FEATURE_DIMENSION
        assert processed.feature_vector.features["cpu_utilization_percent"] == 45.0
        assert processed.feature_vector.features["is_memory_missing"] == 1.0
        assert processed.feature_vector.features["is_disk_missing"] == 1.0
        assert processed.feature_vector.features["is_network_missing"] == 1.0

    def test_validator_catches_out_of_range_values(self) -> None:
        """Validator flags CPU > 100% and negative memory."""
        validator = MetricsValidator()
        bad_metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=150.0, logical_cores=4),
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=-100,
                used_bytes=1100,
                utilization_percent=110.0,
            ),
        )
        result = validator.validate(bad_metrics)
        assert result.has_issues is True
        assert len(result.issues) > 0

    def test_pipeline_reset_clears_rolling_state(self, tmp_path: Path) -> None:
        """Pipeline reset clears rolling buffer history."""
        settings = _make_settings(tmp_path)
        pipeline = PreprocessingPipeline(settings=settings)

        metrics = _make_realistic_metrics()
        pipeline.process(metrics)

        assert pipeline.buffer.sample_count > 0
        pipeline.reset()
        assert pipeline.buffer.sample_count == 0
