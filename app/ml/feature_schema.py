"""Feature schema enforcement, validation, and array conversion subsystem.

Ensures strict feature ordering, dimension consistency (39 numerical features),
and finite value guarantees for machine learning models.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Sequence, Union

import numpy as np

from app.database.models import FeatureVectorRecord
from app.database.schema import FEATURE_COLUMNS
from app.preprocessing.feature_engineer import FeatureVector

EXPECTED_FEATURE_NAMES: list[str] = list(FEATURE_COLUMNS)
FEATURE_DIMENSION: int = len(EXPECTED_FEATURE_NAMES)
EXPECTED_FEATURE_COUNT: int = FEATURE_DIMENSION


def get_feature_names() -> list[str]:
    """Return an immutable copy of the expected ordered feature identifiers."""
    return list(EXPECTED_FEATURE_NAMES)


def validate_feature_vector_finite(features: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate that all features in dictionary have finite numerical values.

    Args:
        features: Dictionary mapping feature names to values.

    Returns:
        Tuple of (is_all_finite, list_of_non_finite_feature_names).
    """
    non_finite = []
    for name in EXPECTED_FEATURE_NAMES:
        if name in features:
            val = features[name]
            try:
                fval = float(val)
                if not math.isfinite(fval):
                    non_finite.append(name)
            except (TypeError, ValueError):
                non_finite.append(name)
    return len(non_finite) == 0, non_finite


def validate_feature_mapping(features: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate that a feature dictionary contains all expected features without non-finite values.

    Args:
        features: Dictionary mapping feature names to numerical values.

    Returns:
        Tuple of (is_valid, list_of_error_messages).
    """
    errors: list[str] = []

    # Check for missing features
    missing = [name for name in EXPECTED_FEATURE_NAMES if name not in features]
    if missing:
        errors.append(f"Feature dictionary is missing required features: {missing[:5]}...")

    # Check for non-finite values (NaN, +inf, -inf)
    is_finite, non_finite = validate_feature_vector_finite(features)
    if not is_finite:
        errors.append(f"Dictionary contains {len(non_finite)} non-finite or non-numeric values: {non_finite[:5]}...")

    return len(errors) == 0, errors


def vector_to_feature_array(
    features: dict[str, Any],
    validate_finite: bool = True,
) -> np.ndarray:
    """Convert an individual feature mapping into a 1x39 2D numpy array.

    Args:
        features: Dictionary mapping feature names to numerical values.
        validate_finite: If True, asserts finite numerical values.

    Returns:
        2D numpy array with shape (1, 39) and dtype float64.

    Raises:
        ValueError: If required features are missing or invalid.
    """
    is_valid, errors = validate_feature_mapping(features)
    if not is_valid:
        raise ValueError(f"Feature schema validation failed: {'; '.join(errors)}")

    ordered_values = [float(features[name]) for name in EXPECTED_FEATURE_NAMES]
    return np.array([ordered_values], dtype=np.float64)


# Alias for backward compatibility
feature_dict_to_array = vector_to_feature_array


def records_to_feature_matrix(
    records: Sequence[Any],
    allow_partial_skip: bool = False,
) -> np.ndarray:
    """Convert a sequence of feature mappings or records into an Nx39 numpy matrix.

    Args:
        records: Sequence of dicts, FeatureVector, or FeatureVectorRecord.
        allow_partial_skip: If True, skips invalid rows rather than raising ValueError.

    Returns:
        Matrix with shape (N, 39) and dtype float64.

    Raises:
        ValueError: If records sequence is empty or rows fail schema validation.
    """
    if not records:
        raise ValueError("Cannot construct feature matrix from empty records sequence.")

    rows: list[list[float]] = []

    for idx, rec in enumerate(records):
        if isinstance(rec, dict):
            feat_dict = rec
        elif hasattr(rec, "features"):
            feat_dict = rec.features
        else:
            feat_dict = {}

        is_valid, errors = validate_feature_mapping(feat_dict)
        if not is_valid:
            if allow_partial_skip:
                continue
            raise ValueError(
                f"Record at index {idx} failed feature schema validation: {'; '.join(errors)}"
            )

        row = [float(feat_dict[name]) for name in EXPECTED_FEATURE_NAMES]
        rows.append(row)

    if not rows:
        raise ValueError("No valid rows remained after applying partial skip filtering.")

    return np.array(rows, dtype=np.float64)


def feature_records_to_matrix(
    records: Sequence[Union[FeatureVectorRecord, FeatureVector]],
) -> tuple[np.ndarray, list[datetime]]:
    """Convert a sequence of feature vector records into an Nx39 numpy matrix and timestamp list.

    Preserves strict temporal ordering and rejects invalid entries.

    Args:
        records: Sequence of FeatureVectorRecord or FeatureVector objects.

    Returns:
        Tuple of (matrix with shape (N, 39), list of timestamps).

    Raises:
        ValueError: If records sequence is empty or schema validation fails.
    """
    if not records:
        raise ValueError("Cannot construct matrix from empty records sequence.")

    matrix = records_to_feature_matrix(records, allow_partial_skip=False)
    timestamps = [rec.timestamp for rec in records]
    return matrix, timestamps

