"""Historical feature data retrieval and preprocessing subsystem.

Interfaces directly with the Phase 4 database persistence service to extract,
validate, and format historical feature vectors into NumPy training matrices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

import numpy as np

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.database.service import PersistenceService
from app.ml.feature_schema import (
    FEATURE_DIMENSION,
    feature_records_to_matrix,
)

logger = get_logger("app.ml.data_loader")


class DataLoaderError(Exception):
    """Base exception for data loading failures."""


class InsufficientDataError(DataLoaderError):
    """Raised when available historical samples are fewer than the required minimum."""


class HistoricalDataLoader:
    """Extracts historical telemetry features from SQLite for machine learning workflows."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        persistence_service: Optional[PersistenceService] = None,
    ) -> None:
        """Initialize the data loader.

        Args:
            settings: Optional application settings container.
            persistence_service: Optional custom PersistenceService instance.
        """
        self.settings: Settings = settings or get_settings()
        self.service: PersistenceService = (
            persistence_service or PersistenceService(settings=self.settings)
        )

    def get_sample_count(self) -> int:
        """Query total stored feature vector count in the database.

        Returns:
            Integer record count.
        """
        try:
            counts = self.service.get_record_counts()
            return counts.get("feature_vectors", 0)
        except Exception as exc:
            logger.error("Failed to query feature_vectors table count: %s", exc)
            return 0

    count_available_samples = get_sample_count


    def has_sufficient_samples(self, min_samples: Optional[int] = None) -> bool:
        """Check if the database contains enough historical records for training.

        Args:
            min_samples: Minimum required count. Defaults to settings.ml_min_training_samples.

        Returns:
            True if sample count >= min_samples, False otherwise.
        """
        threshold = (
            min_samples
            if min_samples is not None
            else self.settings.ml_min_training_samples
        )
        return self.get_sample_count() >= threshold

    def load_feature_matrix(
        self,
        limit: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_samples: Optional[int] = None,
    ) -> tuple[np.ndarray, list[datetime]]:
        """Retrieve historical feature vectors and assemble an Nx39 NumPy matrix.

        Preserves chronological ordering from oldest to newest.

        Args:
            limit: Maximum number of records to retrieve (default: all available).
            start_time: Optional range start timestamp (UTC).
            end_time: Optional range end timestamp (UTC).
            min_samples: Optional threshold. If available records are fewer, raises InsufficientDataError.

        Returns:
            Tuple of (matrix with shape (N, 39), list of timestamps).

        Raises:
            InsufficientDataError: If retrieved samples are fewer than min_samples.
            DataLoaderError: If database read or feature conversion fails.
        """
        threshold = (
            min_samples
            if min_samples is not None
            else self.settings.ml_min_training_samples
        )

        try:
            if start_time is not None and end_time is not None:
                records = self.service.get_features_range(start_time, end_time)
            else:
                max_records = limit if limit is not None else 100_000
                records_desc = self.service.get_latest_features(limit=max_records)
                # Reverse to maintain ascending chronological order
                records = list(reversed(records_desc))

            if len(records) < threshold:
                raise InsufficientDataError(
                    f"Insufficient historical data: found {len(records)} samples, "
                    f"but at least {threshold} are required for training."
                )

            matrix, timestamps = feature_records_to_matrix(records)
            logger.info(
                "Successfully loaded historical feature matrix shape %s across %d timestamps.",
                matrix.shape,
                len(timestamps),
            )
            return matrix, timestamps

        except InsufficientDataError:
            raise
        except Exception as exc:
            logger.error("Failed to load historical feature matrix: %s", exc)
            raise DataLoaderError(f"Failed to load historical feature matrix: {exc}") from exc
