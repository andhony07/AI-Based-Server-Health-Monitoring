"""Telemetry data preprocessing and feature engineering package.

Architectural Responsibility (Phase 3):
- Validate and sanitize incoming host telemetry snapshots.
- Handle missing and invalid domain values with indicator tracking.
- Compute rolling window statistics (mean, min, max) and previous-sample deltas.
- Generate structured, typed FeatureVector objects ready for ML models and persistence.
"""

from __future__ import annotations

from app.preprocessing.cleaner import CleanedSystemMetrics, MetricsCleaner
from app.preprocessing.feature_engineer import FeatureEngineer, FeatureVector
from app.preprocessing.pipeline import PreprocessingPipeline, ProcessedTelemetry
from app.preprocessing.rolling import HistoricalSample, RollingWindowBuffer
from app.preprocessing.validator import (
    MetricsValidator,
    ValidationIssue,
    ValidationResult,
)

__all__ = [
    "CleanedSystemMetrics",
    "FeatureEngineer",
    "FeatureVector",
    "HistoricalSample",
    "MetricsCleaner",
    "MetricsValidator",
    "PreprocessingPipeline",
    "ProcessedTelemetry",
    "RollingWindowBuffer",
    "ValidationIssue",
    "ValidationResult",
]
