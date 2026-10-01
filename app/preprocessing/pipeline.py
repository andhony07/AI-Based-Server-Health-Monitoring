"""Unified preprocessing and feature engineering pipeline coordinator.

Encapsulates data validation, cleaning, missing data handling, rolling window
state management, and feature vector extraction into a single, cohesive interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.models.metrics import SystemMetrics
from app.preprocessing.cleaner import CleanedSystemMetrics, MetricsCleaner
from app.preprocessing.feature_engineer import FeatureEngineer, FeatureVector
from app.preprocessing.rolling import RollingWindowBuffer
from app.preprocessing.validator import MetricsValidator, ValidationResult


@dataclass(frozen=True)
class ProcessedTelemetry:
    """Consolidated result produced by the PreprocessingPipeline.

    Attributes:
        feature_vector: Engineered numerical features ready for ML models.
        validation_result: Detailed validation report identifying anomalies/warnings.
        cleaned_metrics: Sanitized telemetry metrics container.
        raw_metrics: Original SystemMetrics snapshot.
    """

    feature_vector: FeatureVector
    validation_result: ValidationResult
    cleaned_metrics: CleanedSystemMetrics
    raw_metrics: SystemMetrics

    def to_dict(self) -> dict[str, Any]:
        """Convert processed telemetry record into a JSON-compatible dictionary."""
        return {
            "timestamp": self.feature_vector.timestamp.isoformat(),
            "features": self.feature_vector.features,
            "is_valid": self.validation_result.is_valid,
            "validation_issues_count": len(self.validation_result.issues),
            "metadata": self.feature_vector.metadata,
        }


class PreprocessingPipeline:
    """Coordinates metric validation, cleaning, rolling buffer tracking, and feature engineering."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        validator: Optional[MetricsValidator] = None,
        cleaner: Optional[MetricsCleaner] = None,
        rolling_buffer: Optional[RollingWindowBuffer] = None,
    ) -> None:
        """Initialize the preprocessing pipeline.

        Args:
            settings: Optional application settings container.
            validator: Optional custom MetricsValidator instance.
            cleaner: Optional custom MetricsCleaner instance.
            rolling_buffer: Optional custom RollingWindowBuffer instance.
        """
        self.settings: Settings = settings or get_settings()
        self.logger = get_logger("app.preprocessing.pipeline")

        self.validator = validator or MetricsValidator()
        self.cleaner = cleaner or MetricsCleaner(
            missing_value_strategy=self.settings.missing_value_strategy
        )
        self.buffer = rolling_buffer or RollingWindowBuffer(
            window_size=self.settings.rolling_window_size,
            max_history_size=self.settings.max_history_size,
        )
        self.feature_engineer = FeatureEngineer(rolling_buffer=self.buffer)

        self.logger.info(
            "PreprocessingPipeline initialized (window_size=%d, max_history=%d, strategy=%s)",
            self.settings.rolling_window_size,
            self.settings.max_history_size,
            self.settings.missing_value_strategy,
        )

    def process(self, metrics: SystemMetrics) -> ProcessedTelemetry:
        """Execute the end-to-end preprocessing pipeline on a telemetry snapshot.

        Steps:
            1. Validate incoming metrics structure and values.
            2. Clean and impute missing/non-finite fields.
            3. Update rolling buffer and extract engineered numerical features.
            4. Package outputs into a ProcessedTelemetry container.

        Args:
            metrics: Raw SystemMetrics snapshot.

        Returns:
            ProcessedTelemetry containing FeatureVector, validation report, and cleaned metrics.
        """
        # Step 1: Validation
        validation_res = self.validator.validate(metrics)

        # Step 2: Cleaning & Imputation
        cleaned = self.cleaner.clean(metrics, validation_res)

        # Step 3: Feature Engineering
        metadata = {
            "validation_passed": validation_res.is_valid,
            "issues_count": len(validation_res.issues),
            "has_warnings": validation_res.has_issues,
        }
        feature_vec = self.feature_engineer.extract_features(
            cleaned=cleaned, metadata=metadata
        )

        return ProcessedTelemetry(
            feature_vector=feature_vec,
            validation_result=validation_res,
            cleaned_metrics=cleaned,
            raw_metrics=metrics,
        )

    def reset(self) -> None:
        """Reset historical buffer and pipeline state."""
        self.buffer.clear()
        self.logger.info("PreprocessingPipeline state and rolling history reset.")
