"""Unit and integration tests for the PreprocessingPipeline coordinator."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.collectors.system_collector import SystemCollector
from app.core.config import load_config
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.preprocessing.pipeline import PreprocessingPipeline, ProcessedTelemetry


class TestPreprocessingPipeline:
    """Test suite for the unified preprocessing and feature engineering pipeline."""

    def setup_method(self) -> None:
        """Initialize pipeline with custom test settings."""
        self.settings = load_config(
            rolling_window_size=3,
            max_history_size=10,
            missing_value_strategy="zero",
        )
        self.pipeline = PreprocessingPipeline(settings=self.settings)

    def test_pipeline_processes_mock_metrics_cleanly(self) -> None:
        """Verify pipeline transforms raw metrics into valid ProcessedTelemetry."""
        raw = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(
                utilization_percent=50.0,
                logical_cores=4,
                physical_cores=2,
                per_core_percent=[50.0, 50.0, 50.0, 50.0],
            ),
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=400,
                used_bytes=600,
                utilization_percent=60.0,
            ),
        )

        res = self.pipeline.process(raw)

        assert isinstance(res, ProcessedTelemetry)
        assert res.validation_result.is_valid is True
        assert res.feature_vector.get("cpu_utilization_percent") == 50.0
        assert res.feature_vector.get("memory_utilization_percent") == 60.0

        # Verify serialization
        d = res.to_dict()
        assert "timestamp" in d
        assert "features" in d
        assert "is_valid" in d
        assert d["is_valid"] is True

    def test_partial_metric_failure_resilience(self) -> None:
        """Verify pipeline handles corrupted or missing domains without crashing."""
        corrupted = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=None,  # Missing domain
            memory=MemoryMetrics(
                total_bytes=1000,
                available_bytes=500,
                used_bytes=500,
                utilization_percent=float("nan"),  # Non-finite!
            ),
        )

        res = self.pipeline.process(corrupted)

        assert isinstance(res, ProcessedTelemetry)
        # Cleaner should clamp/replace NaN with 0.0
        assert res.cleaned_metrics.memory_percent == 0.0
        # Missing indicators should flag missing CPU
        assert res.feature_vector.get("is_cpu_missing") == 1.0

    def test_pipeline_reset_clears_buffer(self) -> None:
        """Verify reset() empties the internal rolling buffer."""
        raw = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu=CPUMetrics(utilization_percent=10.0, logical_cores=2),
        )
        self.pipeline.process(raw)
        assert self.pipeline.buffer.sample_count == 1

        self.pipeline.reset()
        assert self.pipeline.buffer.sample_count == 0

    def test_live_system_metrics_integration(self) -> None:
        """Verify genuine telemetry collected from the host OS processes through pipeline."""
        collector = SystemCollector()
        raw_live_metrics = collector.collect()

        res = self.pipeline.process(raw_live_metrics)

        assert isinstance(res, ProcessedTelemetry)
        assert res.validation_result.is_valid is True
        assert res.feature_vector is not None
        assert len(res.feature_vector.features) >= 28

        # Verify all feature values are valid finite numbers
        for name, val in res.feature_vector.features.items():
            assert isinstance(val, (int, float)), f"Feature {name} is not numeric"
            assert val == val, f"Feature {name} is NaN"
            assert abs(val) != float("inf"), f"Feature {name} is Inf"
