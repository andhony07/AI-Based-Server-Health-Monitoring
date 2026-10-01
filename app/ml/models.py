"""Typed data representations for machine learning inference, health scoring, and model metadata.

Defines standardized data models for anomaly detection outputs, health scores,
risk classifications, and model serialization metadata.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class RiskCategory(str, Enum):
    """Categorical risk tiers based on anomaly severity and system stress."""

    NORMAL = "Normal"
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(frozen=True)
class AnomalyResult:
    """Outcome of an anomaly detection inference evaluation.

    Attributes:
        is_anomaly: True if the sample is flagged as an outlier/anomaly.
        raw_score: Raw decision function score from the estimator (negative = abnormal).
        normalized_score: Calibrated continuous score in [0.0, 1.0] where 1.0 is most anomalous.
        threshold: The decision threshold applied for binary classification.
    """

    is_anomaly: bool
    raw_score: float
    normalized_score: float
    threshold: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert anomaly result to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class HealthScoreResult:
    """Calculated deterministic system health score report.

    Attributes:
        score: Continuous score in [0.0, 100.0], or None if unavailable.
        status: Status descriptor ('Optimal', 'Good', 'Degraded', 'Critical', or 'unavailable').
        contributing_factors: Dictionary breakdown of deductions (anomaly penalty, resource stress).
        explanation: Human-readable rationale for the score calculation.
    """

    score: Optional[float]
    status: str
    contributing_factors: dict[str, float] = field(default_factory=dict)
    explanation: str = ""

    @property
    def health_score(self) -> Optional[float]:
        """Convenience alias for score."""
        return self.score

    @property
    def anomaly_deduction(self) -> float:
        """Total deduction applied from anomaly detection severity."""
        return self.contributing_factors.get("anomaly_penalty", 0.0)

    @property
    def resource_stress_deduction(self) -> float:
        """Total deduction applied from resource saturation stress."""
        return round(
            self.contributing_factors.get("cpu_stress_penalty", 0.0)
            + self.contributing_factors.get("ram_stress_penalty", 0.0)
            + self.contributing_factors.get("disk_stress_penalty", 0.0),
            2,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert health score result to dictionary."""
        return asdict(self)



@dataclass(frozen=True)
class PredictionResult:
    """Unified result container returned by the ML prediction service for an observation.

    Attributes:
        timestamp: Time of observation (UTC).
        is_anomaly: Binary anomaly flag (True = unusual pattern detected).
        anomaly_score: Normalized anomaly indicator in [0.0, 1.0].
        raw_decision_score: Underlying raw decision function score.
        health_score: Heuristic system health score in [0.0, 100.0], or None.
        risk_category: Assigned RiskCategory tier.
        model_name: Identifier of the serving estimator.
        model_version: Semantic version of the trained model artifact.
        warnings: Informative warnings or notices regarding degraded confidence/missing inputs.
    """

    timestamp: datetime
    is_anomaly: bool
    anomaly_score: float
    raw_decision_score: float
    health_score: Optional[float]
    risk_category: RiskCategory
    model_name: str
    model_version: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert prediction result to a JSON-compatible dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4),
            "raw_decision_score": round(self.raw_decision_score, 4),
            "health_score": round(self.health_score, 2) if self.health_score is not None else None,
            "risk_category": self.risk_category.value,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class ModelMetadata:
    """Companion metadata persisted alongside trained model artifacts.

    Attributes:
        model_name: Name identifier of the model.
        model_type: Algorithm class (e.g., 'IsolationForest').
        version: Model version identifier.
        trained_at: UTC timestamp string of model completion.
        training_samples_count: Number of historical records used during training.
        feature_names: Ordered list of feature names expected by the model.
        hyperparameters: Dictionary of training hyperparameters.
        metrics: Evaluation summary or baseline score distributions.
    """

    model_name: str
    model_type: str
    version: str
    trained_at: str
    training_samples_count: int
    feature_names: list[str]
    hyperparameters: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelMetadata:
        """Instantiate ModelMetadata from a dictionary."""
        return cls(
            model_name=str(data["model_name"]),
            model_type=str(data["model_type"]),
            version=str(data.get("version", "1.0.0")),
            trained_at=str(data["trained_at"]),
            training_samples_count=int(data["training_samples_count"]),
            feature_names=list(data["feature_names"]),
            hyperparameters=dict(data.get("hyperparameters", {})),
            metrics=dict(data.get("metrics", {})),
        )
