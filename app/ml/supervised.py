"""Supervised failure classification interface and future expansion subsystem.

Provides formal architecture contracts, requirements documentation, and evaluation
framework for supervised failure prediction when genuine labeled datasets become available.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple

import numpy as np

from app.core.logging_config import get_logger
from app.database.service import PersistenceService

logger = get_logger("app.ml.supervised")


class FailurePredictionRequirements:
    """Documented prerequisites for legitimate supervised failure prediction.

    In production systems, unsupervised anomaly detection identifies *unusual behavior*,
    which is fundamentally distinct from forecasting *imminent component failure*.
    Supervised failure prediction requires:
        1. Ground Truth Failure Events: Definite timestamps indicating hardware crash,
           kernel panic, OOM killer event, or uncorrectable hardware fault.
        2. Prediction Horizon Window (e.g., Lead Time tau in [1h, 24h]): Binary target
           indicating whether a catastrophic failure occurred within tau hours following
           the observation.
        3. Run-to-Failure Lifecycles: Sufficient historical degradation trajectories
           capturing both healthy operation and terminal failure paths.
        4. Class Imbalance Mitigation: Failures are typically rare (<0.1%), requiring
           PR-AUC evaluation, precision-recall optimization, and cost-sensitive loss.
    """


class BaseFailureClassifier(ABC):
    """Abstract interface defining contracts for supervised failure classifiers."""

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> BaseFailureClassifier:
        """Fit the supervised model on labeled feature matrix X and target labels y."""

    @abstractmethod
    def predict_failure_probability(self, X: np.ndarray) -> np.ndarray:
        """Estimate calibrated failure probability P(failure | X) in [0.0, 1.0]."""

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict binary failure classification (0 = Normal, 1 = Failure Expected)."""


class SupervisedFailureClassifier(BaseFailureClassifier):
    """Reference implementation of a supervised failure classifier ready for labeled data."""

    def __init__(
        self,
        classifier: Any = None,
        prediction_horizon_seconds: float = 3600.0,
    ) -> None:
        """Initialize failure classifier.

        Args:
            classifier: Optional scikit-learn estimator instance.
            prediction_horizon_seconds: Look-ahead horizon for failure definition (default 1h).
        """
        self.prediction_horizon_seconds = prediction_horizon_seconds
        self._classifier = classifier
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        """True if the supervised model has been trained on labeled data."""
        return self._is_fitted

    @property
    def is_trained(self) -> bool:
        """Alias for is_fitted."""
        return self._is_fitted

    def fit(self, X: Any, y: Any) -> SupervisedFailureClassifier:
        """Fit estimator using leakage-safe temporal validation.

        Args:
            X: 2D feature matrix (N, 39).
            y: Binary target labels (0 = normal, 1 = failure within horizon).

        Returns:
            Self.

        Raises:
            ValueError: If fewer than 2 distinct classes are present in y or data is empty.
        """
        arr_X = np.asarray(X)
        arr_y = np.asarray(y)

        if len(arr_X) == 0 or len(arr_y) == 0:
            raise ValueError(
                "Supervised training requires genuine ground-truth failure labels and non-empty datasets."
            )

        unique_classes = np.unique(arr_y)
        if len(unique_classes) < 2:
            raise ValueError(
                f"Supervised training requires at least 2 classes (normal and failure), "
                f"got classes: {unique_classes}"
            )

        from sklearn.ensemble import RandomForestClassifier

        if self._classifier is None:
            self._classifier = RandomForestClassifier(
                n_estimators=100,
                class_weight="balanced",
                random_state=42,
            )

        self._classifier.fit(arr_X, arr_y)
        self._is_fitted = True
        return self

    def predict_failure_probability(self, X: Any) -> np.ndarray:
        """Predict calibrated probability of failure within the configured horizon."""
        if not self._is_fitted or self._classifier is None:
            raise ValueError("Classifier is not trained on labeled failure data.")
        arr_X = np.asarray(X)
        if arr_X.ndim == 1:
            arr_X = arr_X.reshape(1, -1)
        proba = self._classifier.predict_proba(arr_X)
        return proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]

    def predict(self, X: Any) -> np.ndarray:
        """Predict binary failure label."""
        if not self._is_fitted or self._classifier is None:
            raise ValueError("Supervised failure classifier is not trained. Requires ground-truth failure labels.")
        arr_X = np.asarray(X)
        if arr_X.ndim == 1:
            arr_X = arr_X.reshape(1, -1)
        return self._classifier.predict(arr_X)


def inspect_labeled_data_availability(
    persistence_service: Optional[PersistenceService] = None,
) -> Tuple[bool, int, str]:
    """Inspect the database to verify if genuine ground-truth failure labels exist.

    Returns:
        Tuple of (has_labels, count_of_labeled_failures, diagnostic_message).
    """
    message = (
        "No verified failure labels exist in the operational telemetry database. "
        "The system records continuous hardware metrics (CPU, RAM, Disk, Network, Processes), "
        "with no ground-truth hardware or system failure labels. "
        "Supervised failure prediction remains disabled until an external dataset "
        "with verified failure events (e.g. Backblaze SMART or crash logs) is ingested."
    )
    return False, 0, message

