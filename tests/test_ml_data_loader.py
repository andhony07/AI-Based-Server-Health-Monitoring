"""Unit tests for ML historical data loader querying SQLite persistence service."""

from __future__ import annotations

from pathlib import Path
import pytest

from app.core.config import Settings, load_config
from app.database.service import PersistenceService
from app.ml.data_loader import HistoricalDataLoader, InsufficientDataError
from app.ml.feature_schema import EXPECTED_FEATURE_COUNT, EXPECTED_FEATURE_NAMES
from app.models.metrics import (
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    SystemMetrics,
)
from app.preprocessing import PreprocessingPipeline, ProcessedTelemetry


def _create_mock_processed_sample(
    pipeline: PreprocessingPipeline,
    idx: int = 0,
) -> tuple[SystemMetrics, ProcessedTelemetry]:
    """Helper to create a paired SystemMetrics and ProcessedTelemetry."""
    metrics = SystemMetrics(
        cpu=CpuMetrics(utilization_percent=25.0 + (idx % 50), logical_cores=4, per_core_percent=[25.0 + (idx % 50)]),
        memory=MemoryMetrics(total_bytes=16384 * 1024 * 1024, available_bytes=8192 * 1024 * 1024, used_bytes=8192 * 1024 * 1024, utilization_percent=50.0),
        disk=DiskMetrics(total_bytes=10**11, used_bytes=5*10**10, free_bytes=5*10**10, utilization_percent=50.0),
        network=NetworkMetrics(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20),
    )
    processed = pipeline.process(metrics)
    return metrics, processed



@pytest.fixture
def temp_persistence(tmp_path: Path) -> tuple[Settings, PersistenceService]:
    """Fixture providing a temporary SQLite database backed PersistenceService."""
    db_file = tmp_path / "test_loader.db"
    settings = load_config(database_path=str(db_file), models_dir=str(tmp_path / "models"))
    service = PersistenceService(settings=settings)
    return settings, service


class TestHistoricalDataLoader:
    """Tests covering historical feature data loading, sample counting, and InsufficientDataError."""

    def test_count_samples_empty_db(self, temp_persistence: tuple[Settings, PersistenceService]) -> None:
        """Verify sample count is 0 on freshly initialized database."""
        settings, service = temp_persistence
        loader = HistoricalDataLoader(settings=settings, persistence_service=service)
        assert loader.count_available_samples() == 0

    def test_load_feature_matrix_empty_raises(self, temp_persistence: tuple[Settings, PersistenceService]) -> None:
        """Verify InsufficientDataError is raised when trying to load from empty database."""
        settings, service = temp_persistence
        loader = HistoricalDataLoader(settings=settings, persistence_service=service)

        with pytest.raises(InsufficientDataError, match="Insufficient historical data"):
            loader.load_feature_matrix(min_samples=1)

    def test_load_feature_matrix_below_min_samples_raises(
        self,
        temp_persistence: tuple[Settings, PersistenceService],
    ) -> None:
        """Verify InsufficientDataError is raised when samples < min_samples."""
        settings, service = temp_persistence
        loader = HistoricalDataLoader(settings=settings, persistence_service=service)
        pipeline = PreprocessingPipeline(settings=settings)

        # Insert 3 samples
        for i in range(3):
            m, p = _create_mock_processed_sample(pipeline, i)
            service.persist_sample(m, p)

        assert loader.count_available_samples() == 3

        with pytest.raises(InsufficientDataError, match="found 3 samples, but at least 10 are required"):
            loader.load_feature_matrix(min_samples=10)

    def test_load_feature_matrix_success(
        self,
        temp_persistence: tuple[Settings, PersistenceService],
    ) -> None:
        """Verify successfully loading an (N, 39) matrix and associated timestamps."""
        settings, service = temp_persistence
        loader = HistoricalDataLoader(settings=settings, persistence_service=service)
        pipeline = PreprocessingPipeline(settings=settings)

        # Insert 5 samples
        for i in range(5):
            m, p = _create_mock_processed_sample(pipeline, i)
            service.persist_sample(m, p)

        X, timestamps = loader.load_feature_matrix(min_samples=5)
        assert X.shape == (5, EXPECTED_FEATURE_COUNT)
        assert len(timestamps) == 5
        assert X.dtype.name == "float64"

    def test_load_feature_matrix_with_limit(
        self,
        temp_persistence: tuple[Settings, PersistenceService],
    ) -> None:
        """Verify limit parameter caps the returned records."""
        settings, service = temp_persistence
        loader = HistoricalDataLoader(settings=settings, persistence_service=service)
        pipeline = PreprocessingPipeline(settings=settings)

        for i in range(10):
            m, p = _create_mock_processed_sample(pipeline, i)
            service.persist_sample(m, p)

        X, timestamps = loader.load_feature_matrix(limit=4, min_samples=3)
        assert X.shape == (4, EXPECTED_FEATURE_COUNT)
        assert len(timestamps) == 4
