"""Model training and evaluation orchestration subsystem.

Coordinates historical feature extraction from SQLite, training of the Isolation Forest
anomaly detector, baseline score distribution calculation, and model artifact persistence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

import numpy as np

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.ml.anomaly_detector import IsolationForestDetector
from app.ml.data_loader import HistoricalDataLoader, InsufficientDataError
from app.ml.feature_schema import EXPECTED_FEATURE_NAMES
from app.ml.model_manager import ModelManager
from app.ml.models import ModelMetadata

logger = get_logger("app.ml.training")


class ModelTrainer:
    """Orchestrates end-to-end model training from SQLite historical feature store."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        data_loader: Optional[HistoricalDataLoader] = None,
        model_manager: Optional[ModelManager] = None,
    ) -> None:
        """Initialize model trainer.

        Args:
            settings: Application configuration settings container.
            data_loader: HistoricalDataLoader instance.
            model_manager: ModelManager instance.
        """
        self.settings: Settings = settings or get_settings()
        self.data_loader: HistoricalDataLoader = data_loader or HistoricalDataLoader(
            settings=self.settings
        )
        self.model_manager: ModelManager = model_manager or ModelManager(
            settings=self.settings
        )

    def train_isolation_forest(
        self,
        limit: Optional[int] = None,
        min_samples: Optional[int] = None,
        save_artifact: bool = True,
        prefix: str = "isolation_forest",
    ) -> Tuple[IsolationForestDetector, ModelMetadata]:
        """Train and evaluate an IsolationForestDetector from stored feature vectors.

        Args:
            limit: Maximum historical records to pull (default: all).
            min_samples: Minimum required training samples. Defaults to settings.ml_min_training_samples.
            save_artifact: If True, saves model checkpoint and metadata to disk.
            prefix: Artifact filename prefix.

        Returns:
            Tuple of (fitted IsolationForestDetector, ModelMetadata).

        Raises:
            InsufficientDataError: If available records are fewer than min_samples.
        """
        effective_min = (
            min_samples
            if min_samples is not None
            else self.settings.ml_min_training_samples
        )

        logger.info("Starting Isolation Forest training workflow...")

        # 1. Load historical feature vectors from SQLite
        X, timestamps = self.data_loader.load_feature_matrix(
            limit=limit,
            min_samples=effective_min,
        )

        n_samples, n_features = X.shape
        logger.info(
            "Extracted training dataset: %d samples, %d features (temporal span: %s to %s).",
            n_samples,
            n_features,
            timestamps[0].isoformat(),
            timestamps[-1].isoformat(),
        )

        # 2. Instantiate and train detector
        detector = IsolationForestDetector(
            n_estimators=self.settings.ml_isolation_forest_n_estimators,
            contamination=self.settings.ml_isolation_forest_contamination,
            random_state=self.settings.ml_random_seed,
            feature_names=EXPECTED_FEATURE_NAMES,
        )
        detector.fit(X)

        # 3. Compute baseline score distribution on training data
        batch_results = detector.score_batch(X)
        raw_scores = [r.raw_score for r in batch_results]
        norm_scores = [r.normalized_score for r in batch_results]
        anomaly_count = sum(1 for r in batch_results if r.is_anomaly)

        metrics_summary: dict[str, Any] = {
            "training_samples": n_samples,
            "anomalies_flagged_in_training": anomaly_count,
            "anomaly_rate": round(anomaly_count / max(1, n_samples), 4),
            "raw_score_mean": round(float(np.mean(raw_scores)), 4),
            "raw_score_std": round(float(np.std(raw_scores)), 4),
            "normalized_score_mean": round(float(np.mean(norm_scores)), 4),
            "temporal_start": timestamps[0].isoformat(),
            "temporal_end": timestamps[-1].isoformat(),
        }

        metadata = ModelMetadata(
            model_name="IsolationForestDetector",
            model_type="IsolationForest",
            version="1.0.0",
            trained_at=datetime.now(timezone.utc).isoformat(),
            training_samples_count=n_samples,
            feature_names=EXPECTED_FEATURE_NAMES,
            hyperparameters={
                "n_estimators": self.settings.ml_isolation_forest_n_estimators,
                "contamination": self.settings.ml_isolation_forest_contamination,
                "random_state": self.settings.ml_random_seed,
            },
            metrics=metrics_summary,
        )

        # 4. Save checkpoint if requested
        if save_artifact:
            self.model_manager.save_model(
                model=detector.model,
                metadata=metadata,
                prefix=prefix,
            )

        logger.info(
            "Training complete: %d samples trained, baseline anomaly rate: %.2f%%",
            n_samples,
            metrics_summary["anomaly_rate"] * 100,
        )
        return detector, metadata


def main_cli() -> int:
    """CLI entry point for running model training from terminal."""
    parser = argparse.ArgumentParser(description="Train ML anomaly detection model from SQLite telemetry.")
    parser.add_argument("--min-samples", type=int, default=None, help="Minimum required samples to train.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum samples to load.")
    args = parser.parse_args()

    trainer = ModelTrainer()
    try:
        detector, metadata = trainer.train_isolation_forest(
            limit=args.limit,
            min_samples=args.min_samples,
        )
        print(f"Model successfully trained and saved: {metadata.model_name} (v{metadata.version})")
        print(f"Training samples: {metadata.training_samples_count}")
        print(f"Metrics: {metadata.metrics}")
        return 0
    except InsufficientDataError as err:
        print(f"Cannot train model: {err}")
        return 1
    except Exception as exc:
        print(f"Training failed: {exc}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main_cli())
