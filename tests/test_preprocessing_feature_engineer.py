"""Unit tests for the FeatureEngineer."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.preprocessing.cleaner import CleanedSystemMetrics
from app.preprocessing.feature_engineer import FeatureEngineer, FeatureVector
from app.preprocessing.rolling import RollingWindowBuffer


class TestFeatureEngineer:
    """Test suite for numerical feature extraction."""

    def setup_method(self) -> None:
        """Initialize feature engineer with fresh rolling buffer."""
        self.buffer = RollingWindowBuffer(window_size=3, max_history_size=10)
        self.engineer = FeatureEngineer(rolling_buffer=self.buffer)

    def test_feature_extraction_schema_and_types(self) -> None:
        """Verify feature extraction generates all required numerical keys as floats."""
        sample = CleanedSystemMetrics(
            timestamp=datetime(2026, 10, 1, 14, 30, 0, tzinfo=timezone.utc),
            cpu_percent=45.0,
            logical_cores=8,
            per_core_percent=[40.0, 50.0],
            memory_percent=60.0,
            memory_total_mb=16384.0,
            memory_used_mb=9830.4,
            memory_available_mb=6553.6,
            disk_percent=55.0,
            disk_total_gb=500.0,
            disk_used_gb=275.0,
            disk_free_gb=225.0,
            network_sent_bytes_per_sec=1024.0,
            network_recv_bytes_per_sec=2048.0,
            process_count=150,
            top_process_cpu_percent=15.0,
            top_process_memory_percent=8.0,
            top_processes_total_cpu_percent=35.0,
            top_processes_total_memory_percent=25.0,
            is_cpu_missing=0.0,
            is_memory_missing=0.0,
            is_disk_missing=0.0,
            is_network_missing=0.0,
            is_processes_missing=0.0,
        )

        fv = self.engineer.extract_features(sample)

        assert isinstance(fv, FeatureVector)
        assert len(fv.features) >= 28
        assert all(isinstance(v, (int, float)) for v in fv.values)
        assert all(isinstance(k, str) for k in fv.feature_names)

        # Check essential features
        assert fv.get("cpu_utilization_percent") == 45.0
        assert fv.get("cpu_cores_logical") == 8.0
        assert fv.get("memory_utilization_percent") == 60.0
        assert fv.get("memory_used_mb") == 9830.4
        assert fv.get("disk_utilization_percent") == 55.0
        assert fv.get("network_bytes_sent_per_sec") == 1024.0
        assert fv.get("network_bytes_recv_per_sec") == 2048.0
        assert fv.get("process_count") == 150.0
        assert fv.get("top_process_cpu_percent") == 15.0
        assert fv.get("hour_of_day") == 14.0
        assert fv.get("day_of_week") == 3.0  # Thursday
        assert fv.get("is_cpu_missing") == 0.0

    def test_feature_vector_serialization_and_numpy(self) -> None:
        """Verify to_dict and to_numpy serialization methods."""
        sample = CleanedSystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=10.0,
            logical_cores=4,
        )
        fv = self.engineer.extract_features(sample)

        d = fv.to_dict()
        assert isinstance(d, dict)
        assert "timestamp" in d
        assert "features" in d
        assert "metadata" in d

        np_vec = fv.to_numpy()
        assert hasattr(np_vec, "shape")
        assert len(np_vec.shape) == 1
        assert np_vec.shape[0] == len(fv.features)

    def test_delta_and_rolling_calculations_across_sequential_samples(self) -> None:
        """Verify deltas and rolling averages update across sequential samples."""
        t0 = datetime(2026, 10, 1, 10, 0, 0, tzinfo=timezone.utc)
        s1 = CleanedSystemMetrics(
            timestamp=t0,
            cpu_percent=20.0,
            logical_cores=4,
            memory_percent=40.0,
        )
        fv1 = self.engineer.extract_features(s1)
        assert fv1.get("cpu_utilization_delta") == 0.0
        assert fv1.get("cpu_utilization_rolling_mean") == 20.0

        t1 = datetime(2026, 10, 1, 10, 0, 5, tzinfo=timezone.utc)
        s2 = CleanedSystemMetrics(
            timestamp=t1,
            cpu_percent=30.0,
            logical_cores=4,
            memory_percent=42.0,
        )
        fv2 = self.engineer.extract_features(s2)
        assert fv2.get("cpu_utilization_delta") == 10.0  # 30 - 20
        assert fv2.get("cpu_utilization_rolling_mean") == 25.0  # (20 + 30) / 2
        assert fv2.get("cpu_utilization_rolling_max") == 30.0
        assert fv2.get("sample_interval_sec") == 5.0
