"""Feature engineering subsystem for transforming telemetry into ML-ready numerical features.

Extracts immediate observations, delta rates of change, rolling statistical summaries
(mean, min, max), temporal descriptors, and missing indicator flags into a structured
FeatureVector container ready for machine learning inference and historical analysis.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.preprocessing.cleaner import CleanedSystemMetrics
from app.preprocessing.rolling import RollingWindowBuffer


@dataclass(frozen=True)
class FeatureVector:
    """Structured container holding all engineered numerical features for an observation.

    Attributes:
        timestamp: Telemetry sample timestamp (UTC).
        features: Mapping of feature names to engineered float values.
        metadata: Supplementary contextual metadata (e.g., sample count, warnings).
    """

    timestamp: datetime
    features: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def feature_names(self) -> list[str]:
        """Ordered list of feature identifiers."""
        return list(self.features.keys())

    @property
    def values(self) -> list[float]:
        """Ordered list of numerical feature values."""
        return list(self.features.values())

    def get(self, key: str, default: float = 0.0) -> float:
        """Retrieve an individual feature value by name."""
        return self.features.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Convert FeatureVector to a JSON-serializable dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "features": dict(self.features),
            "metadata": dict(self.metadata),
        }

    def to_numpy(self) -> Any:
        """Convert feature values into a 1D NumPy float64 array.

        Returns:
            numpy.ndarray of shape (num_features,).
        """
        import numpy as np

        return np.array(self.values, dtype=np.float64)


class FeatureEngineer:
    """Calculates and assembles domain-specific numerical features and temporal signals."""

    def __init__(self, rolling_buffer: RollingWindowBuffer) -> None:
        """Initialize feature engineer with historical buffer.

        Args:
            rolling_buffer: Active RollingWindowBuffer tracking metric history.
        """
        self.buffer = rolling_buffer

    def extract_features(
        self,
        cleaned: CleanedSystemMetrics,
        metadata: Optional[dict[str, Any]] = None,
    ) -> FeatureVector:
        """Compute all derived features from cleaned metrics and rolling history.

        Args:
            cleaned: CleanedSystemMetrics instance.
            metadata: Optional additional metadata to attach to the FeatureVector.

        Returns:
            Populated FeatureVector containing all numerical features.
        """
        ts = cleaned.timestamp
        ts_utc = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)

        # 1. Update rolling buffer with base measurements for current timestamp
        base_measurements: dict[str, float] = {
            "cpu_percent": cleaned.cpu_percent,
            "memory_percent": cleaned.memory_percent,
            "memory_used_mb": cleaned.memory_used_mb,
            "disk_percent": cleaned.disk_percent,
            "disk_used_gb": cleaned.disk_used_gb,
            "network_sent_bytes_per_sec": cleaned.network_sent_bytes_per_sec,
            "network_recv_bytes_per_sec": cleaned.network_recv_bytes_per_sec,
            "top_process_cpu_percent": cleaned.top_process_cpu_percent,
            "top_process_memory_percent": cleaned.top_process_memory_percent,
        }
        self.buffer.add(timestamp=ts_utc, values=base_measurements)

        # 2. Extract CPU Features
        cpu_features = {
            "cpu_utilization_percent": round(cleaned.cpu_percent, 2),
            "cpu_utilization_delta": self.buffer.get_delta("cpu_percent", default=0.0),
            "cpu_utilization_rolling_mean": self.buffer.get_rolling_mean("cpu_percent"),
            "cpu_utilization_rolling_max": self.buffer.get_rolling_max("cpu_percent"),
            "cpu_utilization_rolling_min": self.buffer.get_rolling_min("cpu_percent"),
            "cpu_cores_logical": float(cleaned.logical_cores),
        }

        # 3. Extract Memory Features
        mem_features = {
            "memory_utilization_percent": round(cleaned.memory_percent, 2),
            "memory_used_mb": round(cleaned.memory_used_mb, 2),
            "memory_available_mb": round(cleaned.memory_available_mb, 2),
            "memory_utilization_delta": self.buffer.get_delta(
                "memory_percent", default=0.0
            ),
            "memory_used_delta_mb": self.buffer.get_delta(
                "memory_used_mb", default=0.0
            ),
            "memory_utilization_rolling_mean": self.buffer.get_rolling_mean(
                "memory_percent"
            ),
            "memory_utilization_rolling_max": self.buffer.get_rolling_max(
                "memory_percent"
            ),
        }

        # 4. Extract Disk Features
        disk_features = {
            "disk_utilization_percent": round(cleaned.disk_percent, 2),
            "disk_used_gb": round(cleaned.disk_used_gb, 2),
            "disk_free_gb": round(cleaned.disk_free_gb, 2),
            "disk_utilization_delta": self.buffer.get_delta(
                "disk_percent", default=0.0
            ),
            "disk_utilization_rolling_mean": self.buffer.get_rolling_mean(
                "disk_percent"
            ),
        }

        # 5. Extract Network Features
        net_features = {
            "network_bytes_sent_per_sec": round(
                cleaned.network_sent_bytes_per_sec, 2
            ),
            "network_bytes_recv_per_sec": round(
                cleaned.network_recv_bytes_per_sec, 2
            ),
            "network_sent_delta_per_sec": self.buffer.get_delta(
                "network_sent_bytes_per_sec", default=0.0
            ),
            "network_recv_delta_per_sec": self.buffer.get_delta(
                "network_recv_bytes_per_sec", default=0.0
            ),
            "network_bytes_sent_rolling_mean": self.buffer.get_rolling_mean(
                "network_sent_bytes_per_sec"
            ),
            "network_bytes_recv_rolling_mean": self.buffer.get_rolling_mean(
                "network_recv_bytes_per_sec"
            ),
            "network_bytes_sent_rolling_max": self.buffer.get_rolling_max(
                "network_sent_bytes_per_sec"
            ),
            "network_bytes_recv_rolling_max": self.buffer.get_rolling_max(
                "network_recv_bytes_per_sec"
            ),
        }

        # 6. Extract Process Features
        proc_features = {
            "process_count": float(cleaned.process_count),
            "top_process_cpu_percent": round(cleaned.top_process_cpu_percent, 2),
            "top_process_memory_percent": round(cleaned.top_process_memory_percent, 2),
            "top_processes_total_cpu_percent": round(
                cleaned.top_processes_total_cpu_percent, 2
            ),
            "top_processes_total_memory_percent": round(
                cleaned.top_processes_total_memory_percent, 2
            ),
        }

        # 7. Extract Temporal Features
        sample_interval = self.buffer.get_time_delta_seconds(default=0.0)
        time_features = {
            "sample_interval_sec": round(sample_interval, 2),
            "hour_of_day": float(ts_utc.hour),
            "day_of_week": float(ts_utc.weekday()),
        }

        # 8. Data Quality / Missing Indicators
        quality_indicators = {
            "is_cpu_missing": cleaned.is_cpu_missing,
            "is_memory_missing": cleaned.is_memory_missing,
            "is_disk_missing": cleaned.is_disk_missing,
            "is_network_missing": cleaned.is_network_missing,
            "is_processes_missing": cleaned.is_processes_missing,
        }

        # Combine all features into ordered mapping
        all_features: dict[str, float] = {}
        all_features.update(cpu_features)
        all_features.update(mem_features)
        all_features.update(disk_features)
        all_features.update(net_features)
        all_features.update(proc_features)
        all_features.update(time_features)
        all_features.update(quality_indicators)

        meta = dict(metadata or {})
        meta["sample_count"] = self.buffer.sample_count
        meta["window_size"] = self.buffer.window_size

        return FeatureVector(
            timestamp=ts_utc,
            features=all_features,
            metadata=meta,
        )
