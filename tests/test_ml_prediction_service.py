"""Unit tests for ML PredictionService orchestration and fallback handling."""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pytest

from app.core.config import Settings, load_config
from app.ml.anomaly_detector import IsolationForestDetector
from app.ml.feature_schema import EXPECTED_FEATURE_COUNT, EXPECTED_FEATURE_NAMES
from app.ml.model_manager import ModelManager
from app.ml.models import ModelMetadata, RiskCategory
from app.ml.prediction_service import PredictionService
from app.models.metrics import (
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    SystemMetrics,
)
from app.preprocessing import (
    CleanedSystemMetrics,
    FeatureVector,
    PreprocessingPipeline,
    ProcessedTelemetry,
    ValidationResult,
)


def _create_sample_processed(
    cpu: float = 25.0,
    mem: float = 40.0,
    disk: float = 30.0,
) -> ProcessedTelemetry:
    """Helper to create a ProcessedTelemetry for prediction testing."""
    metrics = SystemMetrics(
        cpu=CpuMetrics(utilization_percent=cpu, logical_cores=4, per_core_percent=[cpu]),
        memory=MemoryMetrics(total_bytes=16384 * 1024 * 1024, available_bytes=8192 * 1024 * 1024, used_bytes=8192 * 1024 * 1024, utilization_percent=mem),
        disk=DiskMetrics(total_bytes=10**11, used_bytes=3*10**10, free_bytes=7*10**10, utilization_percent=disk),
        network=NetworkMetrics(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20),
    )
    pipeline = PreprocessingPipeline(settings=load_config())
    return pipeline.process(metrics)



class TestPredictionService:
    """Tests covering inference coordination, heuristic fallback, and model reload."""

    def test_predict_without_trained_model_fallback(self, tmp_path: Path) -> None:
        """Verify service falls back to heuristic inference when no model checkpoint exists."""
        settings = load_config(models_dir=str(tmp_path / "models"))
        service = PredictionService(settings=settings)

        assert service.is_model_loaded is False

        sample = _create_sample_processed(cpu=20.0, mem=30.0, disk=25.0)
        prediction = service.predict(sample)

        assert prediction.model_name == "HeuristicFallback"
        assert prediction.anomaly_score is not None
        assert prediction.health_score is not None
        assert 0.0 <= prediction.health_score <= 100.0
        assert prediction.risk_category in list(RiskCategory)
        assert any("No trained Isolation Forest model found" in w for w in prediction.warnings)

    def test_predict_with_trained_model(self, tmp_path: Path) -> None:
        """Verify inference execution when a compatible model checkpoint is loaded."""
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        settings = load_config(models_dir=str(models_dir))

        # Train and save a model
        detector = IsolationForestDetector(n_estimators=20, random_state=42)
        X = np.random.normal(50.0, 5.0, size=(30, EXPECTED_FEATURE_COUNT))
        detector.fit(X)

        manager = ModelManager(settings=settings)
        metadata = ModelMetadata(
            model_name="IsolationForestDetector",
            model_type="IsolationForest",
            version="1.0.0",
            trained_at="2026-10-01T12:00:00Z",
            training_samples_count=30,
            feature_names=EXPECTED_FEATURE_NAMES,
            hyperparameters={"n_estimators": 20},
        )
        manager.save_model(detector.model, metadata, prefix="iso_test")

        # Initialize prediction service
        service = PredictionService(settings=settings)
        assert service.is_model_loaded is True
        assert service.model_name == "IsolationForestDetector"

        sample = _create_sample_processed(cpu=50.0, mem=50.0, disk=50.0)
        res = service.predict(sample)

        assert res.model_name == "IsolationForestDetector"
        assert isinstance(res.is_anomaly, bool)
        assert 0.0 <= res.anomaly_score <= 1.0
        assert res.health_score is not None
        assert 0.0 <= res.health_score <= 100.0
        assert isinstance(res.risk_category, RiskCategory)

    def test_predict_non_finite_features_fallback(self, tmp_path: Path) -> None:
        """Verify non-finite feature values generate warnings and trigger safe fallback."""
        settings = load_config(models_dir=str(tmp_path / "models"))
        service = PredictionService(settings=settings)

        sample = _create_sample_processed()
        sample.feature_vector.features["cpu_utilization_percent"] = float("nan")

        res = service.predict(sample)
        assert any("Non-finite feature values detected" in w for w in res.warnings)
        assert res.risk_category is not None

    def test_reload_model(self, tmp_path: Path) -> None:
        """Verify reload_model hot-swaps new models dynamically."""
        models_dir = tmp_path / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        settings = load_config(models_dir=str(models_dir))

        service = PredictionService(settings=settings)
        assert service.is_model_loaded is False

        # Now save a model
        detector = IsolationForestDetector(n_estimators=10, random_state=42)
        X = np.random.normal(50.0, 5.0, size=(20, EXPECTED_FEATURE_COUNT))
        detector.fit(X)

        manager = ModelManager(settings=settings)
        metadata = ModelMetadata(
            model_name="HotSwappedModel",
            model_type="IsolationForest",
            version="2.0.0",
            trained_at="2026-10-01T12:00:00Z",
            training_samples_count=20,
            feature_names=EXPECTED_FEATURE_NAMES,
            hyperparameters={},
        )
        manager.save_model(detector.model, metadata)

        # Trigger reload
        reloaded = service.reload_model()
        assert reloaded is True
        assert service.is_model_loaded is True
        assert service.model_name == "HotSwappedModel"
