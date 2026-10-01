"""Machine learning, anomaly detection, health scoring, and failure risk analysis subsystem.

Provides Isolation Forest anomaly detection, deterministic transparent health scoring,
standardized risk tier categorization, and historical model training workflows.
"""

from __future__ import annotations

from app.ml.anomaly_detector import (
    AnomalyDetectorError,
    IsolationForestDetector,
    NotFittedError,
)
from app.ml.data_loader import (
    DataLoaderError,
    HistoricalDataLoader,
    InsufficientDataError,
)
from app.ml.feature_schema import (
    EXPECTED_FEATURE_NAMES,
    FEATURE_DIMENSION,
    feature_dict_to_array,
    feature_records_to_matrix,
    get_feature_names,
    validate_feature_mapping,
)
from app.ml.health_score import HealthScoreCalculator
from app.ml.model_manager import (
    IncompatibleModelError,
    ModelManager,
    ModelManagerError,
    ModelNotFoundError,
)
from app.ml.models import (
    AnomalyResult,
    HealthScoreResult,
    ModelMetadata,
    PredictionResult,
    RiskCategory,
)
from app.ml.prediction_service import PredictionService
from app.ml.risk_analyzer import RiskAnalyzer
from app.ml.supervised import (
    BaseFailureClassifier,
    FailurePredictionRequirements,
    SupervisedFailureClassifier,
    inspect_labeled_data_availability,
)
from app.ml.training import ModelTrainer

__all__: list[str] = [
    "AnomalyDetectorError",
    "AnomalyResult",
    "BaseFailureClassifier",
    "DataLoaderError",
    "EXPECTED_FEATURE_NAMES",
    "FEATURE_DIMENSION",
    "FailurePredictionRequirements",
    "HealthScoreCalculator",
    "HealthScoreResult",
    "HistoricalDataLoader",
    "IncompatibleModelError",
    "InsufficientDataError",
    "IsolationForestDetector",
    "ModelManager",
    "ModelManagerError",
    "ModelMetadata",
    "ModelNotFoundError",
    "ModelTrainer",
    "NotFittedError",
    "PredictionResult",
    "PredictionService",
    "RiskAnalyzer",
    "RiskCategory",
    "SupervisedFailureClassifier",
    "feature_dict_to_array",
    "feature_records_to_matrix",
    "get_feature_names",
    "inspect_labeled_data_availability",
    "validate_feature_mapping",
]
