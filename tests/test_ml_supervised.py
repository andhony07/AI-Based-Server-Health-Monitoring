"""Unit tests for supervised failure classification extension point and verification."""

from __future__ import annotations

from pathlib import Path
import pytest

from app.core.config import Settings, load_config
from app.database.service import PersistenceService
from app.ml.supervised import (
    SupervisedFailureClassifier,
    inspect_labeled_data_availability,
)


@pytest.fixture
def temp_service(tmp_path: Path) -> PersistenceService:
    """Fixture providing an active persistence service."""
    settings = load_config(database_path=str(tmp_path / "test_sup.db"), models_dir=str(tmp_path / "models"))
    return PersistenceService(settings=settings)



class TestSupervisedFailureClassification:
    """Tests covering labeled failure data inspection and supervised classifier guardrails."""

    def test_inspect_labeled_data_availability_unlabeled(self, temp_service: PersistenceService) -> None:
        """Verify inspect_labeled_data_availability reports no ground-truth failure labels."""
        has_labels, count, reason = inspect_labeled_data_availability(temp_service)
        assert has_labels is False
        assert count == 0
        assert "no ground-truth hardware or system failure labels" in reason

    def test_supervised_classifier_requires_labeled_data(self) -> None:
        """Verify SupervisedFailureClassifier cannot be fitted without labeled failure datasets."""
        classifier = SupervisedFailureClassifier()
        assert classifier.is_trained is False

        # Fitting with empty or fabricated data should fail or warn
        with pytest.raises(ValueError, match="requires genuine ground-truth failure labels"):
            classifier.fit([], [])

    def test_supervised_classifier_predict_unfitted_raises(self) -> None:
        """Verify calling predict on unfitted classifier raises ValueError."""
        classifier = SupervisedFailureClassifier()
        with pytest.raises(ValueError, match="classifier is not trained"):
            classifier.predict({"cpu_utilization_percent": 50.0})
