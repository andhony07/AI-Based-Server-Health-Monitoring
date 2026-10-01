"""Unit tests for IsolationForest anomaly detection model wrapper."""

from __future__ import annotations

import numpy as np
import pytest

from app.ml.anomaly_detector import IsolationForestDetector
from app.ml.feature_schema import EXPECTED_FEATURE_COUNT, EXPECTED_FEATURE_NAMES


@pytest.fixture
def sample_feature_matrix() -> np.ndarray:
    """Generate a synthetic feature matrix for testing fitting and scoring."""
    np.random.seed(42)
    # Generate 50 samples of 39 features normally distributed around 50
    return np.random.normal(loc=50.0, scale=10.0, size=(50, EXPECTED_FEATURE_COUNT))


class TestIsolationForestDetector:
    """Tests covering IsolationForestDetector initialization, fitting, scoring, and error handling."""

    def test_init_defaults(self) -> None:
        """Verify default parameters are correctly initialized."""
        detector = IsolationForestDetector()
        assert detector.n_estimators == 100
        assert detector.contamination == 0.05
        assert detector.random_state == 42
        assert detector.is_fitted is False
        assert detector.feature_names == EXPECTED_FEATURE_NAMES

    def test_score_sample_before_fit_raises(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify calling score_sample before fit raises ValueError."""
        detector = IsolationForestDetector()
        single_sample = sample_feature_matrix[0:1, :]
        with pytest.raises(ValueError, match="Anomaly detector is not fitted"):
            detector.score_sample(single_sample)

    def test_score_batch_before_fit_raises(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify calling score_batch before fit raises ValueError."""
        detector = IsolationForestDetector()
        with pytest.raises(ValueError, match="Anomaly detector is not fitted"):
            detector.score_batch(sample_feature_matrix)

    def test_fit_and_score_sample(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify fitting on valid matrix and scoring a single sample."""
        detector = IsolationForestDetector(n_estimators=50, random_state=42)
        detector.fit(sample_feature_matrix)
        assert detector.is_fitted is True

        normal_sample = sample_feature_matrix[0:1, :]
        result = detector.score_sample(normal_sample)

        assert isinstance(result.is_anomaly, bool)
        assert isinstance(result.raw_score, float)
        assert isinstance(result.normalized_score, float)
        assert 0.0 <= result.normalized_score <= 1.0

    def test_extreme_outlier_detection(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify that an extreme outlier gets flagged as an anomaly with high normalized score."""
        detector = IsolationForestDetector(n_estimators=100, contamination=0.1, random_state=42)
        detector.fit(sample_feature_matrix)

        # Create an extreme outlier far outside normal distribution
        outlier = np.full((1, EXPECTED_FEATURE_COUNT), 9999.0)
        res = detector.score_sample(outlier)

        assert res.is_anomaly is True
        assert res.raw_score < 0.0
        assert res.normalized_score > 0.6

    def test_dimension_mismatch_raises(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify dimension mismatches raise ValueError during fit or score."""
        detector = IsolationForestDetector()
        wrong_fit_matrix = np.ones((20, 10))  # 10 features instead of 39

        with pytest.raises(ValueError, match="Feature dimension mismatch"):
            detector.fit(wrong_fit_matrix)

        detector.fit(sample_feature_matrix)
        wrong_sample = np.ones((1, 25))
        with pytest.raises(ValueError, match="Expected input shape"):
            detector.score_sample(wrong_sample)

    def test_fit_insufficient_samples_raises(self) -> None:
        """Verify fit raises ValueError if passed empty or single sample."""
        detector = IsolationForestDetector()
        with pytest.raises(ValueError, match="Insufficient samples to fit"):
            detector.fit(np.zeros((1, EXPECTED_FEATURE_COUNT)))


    def test_deterministic_results(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify deterministic outputs across different detector instances with the same seed."""
        det1 = IsolationForestDetector(n_estimators=50, random_state=123)
        det2 = IsolationForestDetector(n_estimators=50, random_state=123)

        det1.fit(sample_feature_matrix)
        det2.fit(sample_feature_matrix)

        sample = sample_feature_matrix[5:6, :]
        res1 = det1.score_sample(sample)
        res2 = det2.score_sample(sample)

        assert res1.is_anomaly == res2.is_anomaly
        assert pytest.approx(res1.raw_score, abs=1e-5) == res2.raw_score
        assert pytest.approx(res1.normalized_score, abs=1e-5) == res2.normalized_score

    def test_score_batch(self, sample_feature_matrix: np.ndarray) -> None:
        """Verify batch scoring processes all rows and produces matching results."""
        detector = IsolationForestDetector(n_estimators=50, random_state=42)
        detector.fit(sample_feature_matrix)

        batch_res = detector.score_batch(sample_feature_matrix)
        assert len(batch_res) == len(sample_feature_matrix)
        for res in batch_res:
            assert 0.0 <= res.normalized_score <= 1.0
