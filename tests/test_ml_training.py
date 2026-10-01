"""Unit and integration tests for ML model training and evaluation workflows."""

from __future__ import annotations

from pathlib import Path
import pytest

from app.core.config import Settings, load_config
from app.database.service import PersistenceService
from app.ml.anomaly_detector import IsolationForestDetector
from app.ml.data_loader import HistoricalDataLoader, InsufficientDataError
from app.ml.feature_schema import EXPECTED_FEATURE_NAMES
from app.ml.model_manager import ModelManager
from app.ml.training import ModelTrainer, main_cli
from app.models.metrics import (
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    SystemMetrics,
)
from app.preprocessing import (
    PreprocessingPipeline,
    ProcessedTelemetry,
)


def _insert_samples(service: PersistenceService, count: int) -> None:
    """Helper to insert synthetic feature samples into SQLite."""
    pipeline = PreprocessingPipeline(settings=service.settings)
    for i in range(count):
        metrics = SystemMetrics(
            cpu=CpuMetrics(utilization_percent=20.0 + (i % 30), logical_cores=4, per_core_percent=[20.0 + (i % 30)]),
            memory=MemoryMetrics(total_bytes=16384 * 1024 * 1024, available_bytes=8192 * 1024 * 1024, used_bytes=8192 * 1024 * 1024, utilization_percent=50.0),
            disk=DiskMetrics(total_bytes=10**11, used_bytes=5*10**10, free_bytes=5*10**10, utilization_percent=50.0),
            network=NetworkMetrics(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20),
        )
        processed = pipeline.process(metrics)
        service.persist_sample(metrics, processed)


class TestModelTraining:
    """Tests covering end-to-end model training, checkpoint persistence, and validation."""

    def test_train_insufficient_data_raises(self, tmp_path: Path) -> None:
        """Verify train_isolation_forest raises InsufficientDataError when SQLite has too few records."""
        settings = load_config(
            database_path=str(tmp_path / "train_empty.db"),
            models_dir=str(tmp_path / "models"),
            ml_min_training_samples=10,
        )
        service = PersistenceService(settings=settings)
        # Insert only 3 samples
        _insert_samples(service, count=3)

        trainer = ModelTrainer(settings=settings)
        with pytest.raises(InsufficientDataError, match="at least 10 are required"):
            trainer.train_isolation_forest(min_samples=10)

    def test_train_isolation_forest_success(self, tmp_path: Path) -> None:
        """Verify training succeeds, evaluates baseline metrics, and saves checkpoint artifacts."""
        settings = load_config(
            database_path=str(tmp_path / "train_success.db"),
            models_dir=str(tmp_path / "models"),
            ml_min_training_samples=15,
            ml_isolation_forest_n_estimators=25,
        )
        service = PersistenceService(settings=settings)
        _insert_samples(service, count=20)

        trainer = ModelTrainer(settings=settings)
        detector, metadata = trainer.train_isolation_forest(min_samples=15, save_artifact=True)

        assert isinstance(detector, IsolationForestDetector)
        assert detector.is_fitted is True
        assert metadata.training_samples_count == 20
        assert metadata.model_type == "IsolationForest"
        assert "anomaly_rate" in metadata.metrics
        assert "normalized_score_mean" in metadata.metrics

        # Verify artifacts written to models directory
        models_dir = Path(settings.models_dir)
        joblib_files = list(models_dir.glob("*.joblib"))
        meta_files = list(models_dir.glob("*.json"))
        assert len(joblib_files) == 1
        assert len(meta_files) == 1

