"""Isolation Forest anomaly detection model wrapper and scoring subsystem.

Leverages scikit-learn's IsolationForest to identify statistically anomalous
operational patterns across the 39-feature telemetry space.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
from sklearn.ensemble import IsolationForest

from app.core.logging_config import get_logger
from app.ml.feature_schema import EXPECTED_FEATURE_NAMES, FEATURE_DIMENSION
from app.ml.models import AnomalyResult

logger = get_logger("app.ml.anomaly_detector")


class NotFittedError(ValueError):
    """Raised when inference is attempted on an unfitted detector."""


class AnomalyDetectorError(Exception):
    """Base exception for anomaly detector failures."""


class IsolationForestDetector:
    """Configurable Isolation Forest anomaly detector for system telemetry."""

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.05,
        random_state: int = 42,
        feature_names: Optional[list[str]] = None,
    ) -> None:
        """Initialize the Isolation Forest detector.

        Args:
            n_estimators: Number of decision trees in the ensemble.
            contamination: Expected fraction of outliers in training data.
            random_state: Seed for reproducible tree generation.
            feature_names: Ordered list of feature names expected by this model.
        """
        self.n_estimators: int = n_estimators
        self.contamination: float = contamination
        self.random_state: int = random_state
        self.feature_names: list[str] = list(feature_names or EXPECTED_FEATURE_NAMES)
        self.model: Optional[IsolationForest] = None
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        """True if the underlying model has been trained and is ready for inference."""
        return self._is_fitted

    def fit(self, X: np.ndarray) -> IsolationForestDetector:
        """Train the Isolation Forest estimator on historical feature vectors.

        Args:
            X: 2D NumPy array with shape (N, 39).

        Returns:
            Self (fitted instance).

        Raises:
            ValueError: If input dimensions or sample counts are invalid.
        """
        if not isinstance(X, np.ndarray):
            X = np.asarray(X, dtype=np.float64)

        if X.ndim != 2:
            raise ValueError(f"Expected 2D feature matrix (samples, features), got ndim={X.ndim}")

        n_samples, n_features = X.shape
        if n_features != FEATURE_DIMENSION:
            raise ValueError(
                f"Feature dimension mismatch: expected {FEATURE_DIMENSION} columns, "
                f"got {n_features} columns."
            )

        if n_samples < 2:
            raise ValueError(f"Insufficient samples to fit Isolation Forest: {n_samples} provided.")

        logger.info(
            "Fitting IsolationForestDetector (n_samples=%d, n_estimators=%d, contamination=%.3f, seed=%d)...",
            n_samples,
            self.n_estimators,
            self.contamination,
            self.random_state,
        )

        estimator = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        estimator.fit(X)

        self.model = estimator
        self._is_fitted = True
        logger.info("IsolationForestDetector fitted successfully.")
        return self

    def score_sample(self, X: np.ndarray) -> AnomalyResult:
        """Evaluate an individual observation and return structured anomaly metrics.

        Args:
            X: 2D NumPy array with shape (1, 39) or 1D array of length 39.

        Returns:
            Populated AnomalyResult containing raw decision score and normalized anomaly score.

        Raises:
            NotFittedError: If the model has not been trained.
            ValueError: If input dimensions do not match 39 features.
        """
        if not self._is_fitted or self.model is None:
            raise NotFittedError(
                "Anomaly detector is not fitted. Train the model using fit() or load a checkpoint."
            )

        if not isinstance(X, np.ndarray):
            X = np.asarray(X, dtype=np.float64)

        if X.ndim == 1:
            X = X.reshape(1, -1)

        if X.shape != (1, FEATURE_DIMENSION):
            raise ValueError(
                f"Expected input shape (1, {FEATURE_DIMENSION}), got {X.shape}"
            )

        # In scikit-learn IsolationForest:
        # decision_function: negative scores = anomalies; positive scores = inliers/normal.
        # predict: -1 = anomaly, 1 = normal.
        raw_score = float(self.model.decision_function(X)[0])
        pred_label = int(self.model.predict(X)[0])
        is_anomaly = bool(pred_label == -1)

        # Normalize score into [0.0, 1.0] where 1.0 represents highest anomaly severity.
        # We apply an inverted logistic transformation centered at 0.0 with scaling factor k=8.0:
        # score = 0.0 -> normalized = 0.50 (the decision boundary)
        # score = +0.20 (normal) -> normalized ~ 0.17
        # score = -0.20 (outlier) -> normalized ~ 0.83
        k = 8.0
        try:
            normalized_score = 1.0 / (1.0 + math.exp(k * raw_score))
        except OverflowError:
            normalized_score = 1.0 if raw_score < 0 else 0.0

        normalized_score = max(0.0, min(1.0, normalized_score))

        return AnomalyResult(
            is_anomaly=is_anomaly,
            raw_score=round(raw_score, 4),
            normalized_score=round(normalized_score, 4),
            threshold=0.0,
        )

    def score_batch(self, X: np.ndarray) -> list[AnomalyResult]:
        """Evaluate a batch of observations and return an AnomalyResult for each.

        Args:
            X: 2D NumPy array with shape (N, 39).

        Returns:
            List of AnomalyResult objects corresponding to each row.
        """
        if not self._is_fitted or self.model is None:
            raise NotFittedError("Anomaly detector is not fitted.")

        if not isinstance(X, np.ndarray):
            X = np.asarray(X, dtype=np.float64)

        if X.ndim != 2 or X.shape[1] != FEATURE_DIMENSION:
            raise ValueError(
                f"Expected matrix with shape (N, {FEATURE_DIMENSION}), got {X.shape}"
            )

        raw_scores = self.model.decision_function(X)
        pred_labels = self.model.predict(X)

        results: list[AnomalyResult] = []
        k = 8.0
        for raw, pred in zip(raw_scores, pred_labels):
            is_anomaly = bool(pred == -1)
            try:
                norm = 1.0 / (1.0 + math.exp(k * float(raw)))
            except OverflowError:
                norm = 1.0 if raw < 0 else 0.0
            norm = max(0.0, min(1.0, norm))

            results.append(
                AnomalyResult(
                    is_anomaly=is_anomaly,
                    raw_score=round(float(raw), 4),
                    normalized_score=round(norm, 4),
                    threshold=0.0,
                )
            )

        return results
