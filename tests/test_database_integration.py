"""Integration tests for end-to-end telemetry collection, preprocessing, and database persistence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.collectors.system_collector import SystemCollector
from app.core.config import Settings, load_config
from app.database.connection import get_connection
from app.database.service import PersistenceService
from app.main import main
from app.preprocessing.pipeline import PreprocessingPipeline


@pytest.fixture
def integrated_settings(tmp_path: Path) -> Settings:
    """Provide isolated application settings with temporary directories and database."""
    base_dir = tmp_path / "app_root"
    db_file = base_dir / "data" / "integration_test.db"
    return load_config(
        base_dir=base_dir,
        database_path=str(db_file),
        db_connection_timeout=5.0,
        db_auto_init=True,
    )


class TestDatabaseIntegration:
    """Test suite verifying end-to-end data flow from collectors through persistence."""

    def test_collector_pipeline_persistence_end_to_end(
        self, integrated_settings: Settings
    ) -> None:
        """Verify real telemetry collection processes through pipeline and persists in database."""
        integrated_settings.ensure_directories()

        collector = SystemCollector(settings=integrated_settings)
        pipeline = PreprocessingPipeline(settings=integrated_settings)
        db_service = PersistenceService(settings=integrated_settings)

        # 1. Collect real telemetry
        raw_metrics = collector.collect()
        assert raw_metrics is not None
        assert raw_metrics.cpu is not None

        # 2. Preprocess telemetry
        processed = pipeline.process(raw_metrics)
        assert len(processed.feature_vector.features) == 39
        assert processed.validation_result is not None

        # 3. Persist to database
        res = db_service.persist_sample(raw_metrics, processed)
        assert res.success is True
        assert res.metric_id is not None
        assert res.feature_id is not None
        assert res.validation_id is not None

        # 4. Verify in database
        latest_metrics = db_service.get_latest_metrics(limit=1)
        latest_features = db_service.get_latest_features(limit=1)
        latest_logs = db_service.get_latest_validation_logs(limit=1)

        assert len(latest_metrics) == 1
        assert latest_metrics[0].id == res.metric_id
        assert len(latest_features) == 1
        assert latest_features[0].id == res.feature_id
        assert latest_features[0].metric_id == res.metric_id
        assert len(latest_logs) == 1
        assert latest_logs[0].id == res.validation_id
        assert latest_logs[0].metric_id == res.metric_id

    def test_foreign_key_cascade_deletion(
        self, integrated_settings: Settings
    ) -> None:
        """Verify deleting a system_metrics record cascades to delete linked feature_vectors and validation_logs."""
        integrated_settings.ensure_directories()
        collector = SystemCollector(settings=integrated_settings)
        pipeline = PreprocessingPipeline(settings=integrated_settings)
        db_service = PersistenceService(settings=integrated_settings)

        # Collect and persist a sample
        raw_metrics = collector.collect()
        processed = pipeline.process(raw_metrics)
        res = db_service.persist_sample(raw_metrics, processed)
        assert res.success is True
        metric_id = res.metric_id

        # Confirm 1 record exists in each table
        counts = db_service.get_record_counts()
        assert counts["system_metrics"] == 1
        assert counts["feature_vectors"] == 1
        assert counts["validation_logs"] == 1

        # Delete the system_metrics record directly
        with get_connection(db_service.db_path) as conn:
            conn.execute("DELETE FROM system_metrics WHERE id = ?;", (metric_id,))

        # Verify cascade delete removed dependent rows
        counts_after = db_service.get_record_counts()
        assert counts_after["system_metrics"] == 0
        assert counts_after["feature_vectors"] == 0
        assert counts_after["validation_logs"] == 0

    def test_main_single_shot_persists_sample(
        self, integrated_settings: Settings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify main(single_shot=True) executes and persists a sample to the configured database."""
        monkeypatch.setenv("DATA_DIR", str(integrated_settings.data_dir))
        monkeypatch.setenv("DB_PATH", str(integrated_settings.database_path))

        exit_code = main(single_shot=True)
        assert exit_code == 0

        # Verify sample was written to the DB
        assert integrated_settings.database_path.exists()
        db_service = PersistenceService(settings=integrated_settings)
        counts = db_service.get_record_counts()
        assert counts["system_metrics"] >= 1
        assert counts["feature_vectors"] >= 1
        assert counts["validation_logs"] >= 1
