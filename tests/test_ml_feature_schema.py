"""Unit tests for ML feature schema enforcement and matrix conversions."""

from __future__ import annotations

import math
import numpy as np
import pytest

from app.ml.feature_schema import (
    EXPECTED_FEATURE_COUNT,
    EXPECTED_FEATURE_NAMES,
    records_to_feature_matrix,
    validate_feature_vector_finite,
    vector_to_feature_array,
)


def _generate_valid_feature_dict() -> dict[str, float]:
    """Helper to generate a dictionary of valid features matching the 39-feature schema."""
    return {name: float(idx * 1.5) for idx, name in enumerate(EXPECTED_FEATURE_NAMES)}


class TestFeatureSchema:
    """Tests covering schema definition, dimensions, and conversion logic."""

    def test_expected_feature_count(self) -> None:
        """Verify the expected feature count is exactly 39."""
        assert EXPECTED_FEATURE_COUNT == 39
        assert len(EXPECTED_FEATURE_NAMES) == 39

    def test_vector_to_feature_array_valid(self) -> None:
        """Verify converting a complete dictionary yields a (1, 39) numpy array in correct order."""
        feature_dict = _generate_valid_feature_dict()
        arr = vector_to_feature_array(feature_dict)

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (1, 39)
        assert arr.dtype == np.float64
        # Verify first and last values correspond to the ordered dict keys
        assert arr[0, 0] == 0.0
        assert arr[0, 1] == 1.5

    def test_vector_to_feature_array_missing_feature(self) -> None:
        """Verify ValueError is raised if any schema feature is absent."""
        feature_dict = _generate_valid_feature_dict()
        del feature_dict["cpu_utilization_percent"]

        with pytest.raises(ValueError, match="Feature dictionary is missing required features"):
            vector_to_feature_array(feature_dict)

    def test_vector_to_feature_array_non_finite_rejected(self) -> None:
        """Verify NaN or Inf values raise ValueError when validate_finite is True."""
        feature_dict = _generate_valid_feature_dict()
        feature_dict["cpu_utilization_percent"] = float("nan")

        with pytest.raises(ValueError, match="contains 1 non-finite"):
            vector_to_feature_array(feature_dict, validate_finite=True)

        feature_dict["cpu_utilization_percent"] = float("inf")
        with pytest.raises(ValueError, match="contains 1 non-finite"):
            vector_to_feature_array(feature_dict, validate_finite=True)

    def test_validate_feature_vector_finite(self) -> None:
        """Verify validate_feature_vector_finite detects and lists non-finite entries."""
        valid_dict = _generate_valid_feature_dict()
        is_finite, non_finites = validate_feature_vector_finite(valid_dict)
        assert is_finite is True
        assert len(non_finites) == 0

        invalid_dict = _generate_valid_feature_dict()
        invalid_dict["memory_utilization_percent"] = float("nan")
        invalid_dict["disk_utilization_percent"] = float("-inf")
        is_finite, non_finites = validate_feature_vector_finite(invalid_dict)
        assert is_finite is False
        assert "memory_utilization_percent" in non_finites
        assert "disk_utilization_percent" in non_finites

    def test_records_to_feature_matrix_valid(self) -> None:
        """Verify converting multiple feature records yields an (N, 39) matrix."""
        records = [
            _generate_valid_feature_dict(),
            _generate_valid_feature_dict(),
            _generate_valid_feature_dict(),
        ]
        matrix = records_to_feature_matrix(records)
        assert matrix.shape == (3, 39)
        assert matrix.dtype == np.float64

    def test_records_to_feature_matrix_empty_raises(self) -> None:
        """Verify converting empty record set raises ValueError."""
        with pytest.raises(ValueError, match="Cannot construct feature matrix from empty records"):
            records_to_feature_matrix([])

    def test_records_to_feature_matrix_skips_invalid_when_requested(self) -> None:
        """Verify allow_partial_skip drops rows with non-finite values."""
        good_1 = _generate_valid_feature_dict()
        bad = _generate_valid_feature_dict()
        bad["cpu_utilization_percent"] = float("nan")
        good_2 = _generate_valid_feature_dict()

        matrix = records_to_feature_matrix([good_1, bad, good_2], allow_partial_skip=True)
        assert matrix.shape == (2, 39)
