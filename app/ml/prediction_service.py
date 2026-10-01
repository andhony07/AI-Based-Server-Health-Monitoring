"""Machine learning prediction service coordinator.

Coordinates model inference, anomaly evaluation, transparent health score calculation,
and operational risk tier classification for real-time telemetry frames.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Union

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.ml.anomaly_detector import IsolationForestDetector
from app.ml.feature_schema import (
    feature_dict_to_array,
    validate_feature_mapping,
)
from app.ml.health_score import HealthScoreCalculator
from app.ml.model_manager import ModelManager, ModelManagerError, ModelNotFoundError
from app.ml.models import (
    AnomalyResult,
    ModelMetadata,
    PredictionResult,
    RiskCategory,
)
from app.ml.risk_analyzer import RiskAnalyzer
from app.preprocessing.feature_engineer import FeatureVector
from app.preprocessing.pipeline import ProcessedTelemetry

logger = get_logger("app.ml.prediction_service")


class PredictionService:
    """High-level service coordinating model loading, inference, health scoring, and risk analysis."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        model_manager: Optional[ModelManager] = None,
        detector: Optional[IsolationForestDetector] = None,
        health_calculator: Optional[HealthScoreCalculator] = None,
        risk_analyzer: Optional[RiskAnalyzer] = None,
        auto_load: bool = True,
    ) -> None:
        """Initialize the prediction service.

        Args:
            settings: Application configuration settings container.
            model_manager: ModelManager instance for checkpoint loading.
            detector: Optional pre-fitted IsolationForestDetector instance.
            health_calculator: HealthScoreCalculator instance.
            risk_analyzer: RiskAnalyzer instance.
            auto_load: If True, attempts to load a saved checkpoint on initialization.
        """
        self.settings: Settings = settings or get_settings()
        self.model_manager: ModelManager = model_manager or ModelManager(settings=self.settings)
        self.detector: Optional[IsolationForestDetector] = detector
        self.health_calculator: HealthScoreCalculator = health_calculator or HealthScoreCalculator()
        self.risk_analyzer: RiskAnalyzer = risk_analyzer or RiskAnalyzer(settings=self.settings)
        self.metadata: Optional[ModelMetadata] = None

        if self.detector is None and auto_load:
            self.load_active_model()

    @property
    def is_model_loaded(self) -> bool:
        """True if an active detector model is loaded and ready for inference."""
        return self.is_model_ready()

    @property
    def model_name(self) -> str:
        """Name of the currently active model."""
        if self.metadata:
            return self.metadata.model_name
        return "HeuristicBaseline"

    def is_model_ready(self) -> bool:
        """True if an active, fitted detector model is loaded and ready for inference."""
        return self.detector is not None and self.detector.is_fitted

    def reload_model(self, prefix: Optional[str] = None) -> bool:
        """Reload the latest or specified model checkpoint into the active service.

        Args:
            prefix: Optional artifact filename prefix. If None, loads the latest checkpoint.

        Returns:
            True if a model was successfully loaded, False otherwise.
        """
        if prefix is not None:
            return self.load_active_model(prefix)

        latest = self.model_manager.load_latest_model()
        if latest is not None:
            raw_model, metadata = latest
            detector = IsolationForestDetector(
                n_estimators=metadata.hyperparameters.get("n_estimators", 100),
                contamination=metadata.hyperparameters.get("contamination", 0.05),
                random_state=metadata.hyperparameters.get("random_state", 42),
                feature_names=metadata.feature_names,
            )
            detector.model = raw_model
            detector._is_fitted = True

            self.detector = detector
            self.metadata = metadata
            logger.info("PredictionService reloaded model '%s' (v%s).", metadata.model_name, metadata.version)
            return True
        return False

    def load_active_model(self, prefix: Optional[str] = None) -> bool:
        """Attempt to load a trained model checkpoint from the model directory.

        Args:
            prefix: Artifact filename prefix. If None, checks 'isolation_forest' then newest available.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        target_prefix = prefix or "isolation_forest"
        if not self.model_manager.has_model(target_prefix):
            if prefix is None:
                latest = self.model_manager.load_latest_model()
                if latest is not None:
                    raw_model, metadata = latest
                    detector = IsolationForestDetector(
                        n_estimators=metadata.hyperparameters.get("n_estimators", 100),
                        contamination=metadata.hyperparameters.get("contamination", 0.05),
                        random_state=metadata.hyperparameters.get("random_state", 42),
                        feature_names=metadata.feature_names,
                    )
                    detector.model = raw_model
                    detector._is_fitted = True
                    self.detector = detector
                    self.metadata = metadata
                    logger.info("PredictionService auto-loaded latest model '%s'.", metadata.model_name)
                    return True
            logger.debug("No trained model checkpoint found at prefix '%s'.", target_prefix)
            return False

        try:
            raw_model, metadata = self.model_manager.load_model(target_prefix)
            detector = IsolationForestDetector(
                n_estimators=metadata.hyperparameters.get("n_estimators", 100),
                contamination=metadata.hyperparameters.get("contamination", 0.05),
                random_state=metadata.hyperparameters.get("random_state", 42),
                feature_names=metadata.feature_names,
            )
            detector.model = raw_model
            detector._is_fitted = True

            self.detector = detector
            self.metadata = metadata
            logger.info(
                "PredictionService successfully loaded model '%s' (v%s, trained on %d samples).",
                metadata.model_name,
                metadata.version,
                metadata.training_samples_count,
            )
            return True
        except (ModelNotFoundError, ModelManagerError) as err:
            logger.warning("Could not load model checkpoint '%s': %s", target_prefix, err)
            return False

    def predict(
        self,
        telemetry: Union[ProcessedTelemetry, FeatureVector, dict[str, Any]],
    ) -> PredictionResult:
        """Generate full ML health predictions, anomaly scores, and risk classifications for a sample.

        If a trained ML model is unavailable, gracefully computes fallback health scores
        and risk categorizations using hardware saturation signals, reporting a warning.

        Args:
            telemetry: ProcessedTelemetry, FeatureVector, or raw feature mapping dictionary.

        Returns:
            Populated PredictionResult.
        """
        # Extract features dictionary and timestamp
        timestamp = datetime.now(timezone.utc)
        if isinstance(telemetry, ProcessedTelemetry):
            features = telemetry.feature_vector.features
            timestamp = telemetry.feature_vector.timestamp
        elif isinstance(telemetry, FeatureVector):
            features = telemetry.features
            timestamp = telemetry.timestamp
        elif isinstance(telemetry, dict):
            features = telemetry
            if "timestamp" in telemetry and isinstance(telemetry["timestamp"], datetime):
                timestamp = telemetry["timestamp"]
        else:
            raise TypeError(f"Unsupported telemetry input type: {type(telemetry)}")

        warnings: list[str] = []
        anomaly_res: Optional[AnomalyResult] = None

        from app.ml.feature_schema import validate_feature_vector_finite
        is_finite, non_finites = validate_feature_vector_finite(features)
        if not is_finite:
            warnings.append(f"Non-finite feature values detected in: {non_finites[:3]}")

        # 1. Run ML Anomaly Detection if model is available and features are valid
        if self.is_model_ready() and self.detector is not None:
            if is_finite:
                try:
                    X = feature_dict_to_array(features)
                    anomaly_res = self.detector.score_sample(X)
                except Exception as exc:
                    logger.error("Error during anomaly scoring: %s", exc)
                    warnings.append(f"Anomaly scoring failed: {exc}")
            else:
                warnings.append("Anomaly scoring skipped due to non-finite feature values.")
        else:
            warnings.append("No trained Isolation Forest model found or loaded; running in heuristic fallback mode.")

        # 2. Compute Health Score
        health_res = self.health_calculator.calculate(
            anomaly_result=anomaly_res,
            features=features,
        )

        # 3. Determine Risk Category
        risk_cat = self.risk_analyzer.evaluate_risk(
            anomaly_input=anomaly_res,
            health_result=health_res,
            features=features,
        )

        model_name = self.metadata.model_name if self.metadata else "HeuristicFallback"
        model_version = self.metadata.version if self.metadata else "0.0.0"

        return PredictionResult(
            timestamp=timestamp,
            is_anomaly=anomaly_res.is_anomaly if anomaly_res else False,
            anomaly_score=anomaly_res.normalized_score if anomaly_res else 0.0,
            raw_decision_score=anomaly_res.raw_score if anomaly_res else 0.0,
            health_score=health_res.score,
            risk_category=risk_cat,
            model_name=model_name,
            model_version=model_version,
            warnings=warnings,
        )

