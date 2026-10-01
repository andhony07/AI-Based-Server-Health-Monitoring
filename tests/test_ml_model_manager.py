"""Unit tests for ML model persistence, metadata validation, and version management."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from sklearn.ensemble import IsolationForest

from app.core.config import Settings, load_config
from app.ml.feature_schema import EXPECTED_FEATURE_NAMES
from app.ml.model_manager import (
    IncompatibleModelError,
    ModelManager,
    ModelSerializationError,
)
from app.ml.models import ModelMetadata


@pytest.fixture
def temp_models_dir(tmp_path: Path) -> Path:
    """Fixture providing a temporary directory for model artifacts."""
    models_path = tmp_path / "models"
    models_path.mkdir(parents=True, exist_ok=True)
    return models_path


@pytest.fixture
def dummy_model() -> IsolationForest:
    """Fixture providing a simple fitted IsolationForest model."""
    import numpy as np
    model = IsolationForest(n_estimators=10, random_state=42)
    X = np.random.normal(50.0, 10.0, size=(20, len(EXPECTED_FEATURE_NAMES)))
    model.fit(X)
    return model


@pytest.fixture
def dummy_metadata() -> ModelMetadata:
    """Fixture providing standard valid model metadata."""
    return ModelMetadata(
        model_name="IsolationForestDetector",
        model_type="IsolationForest",
        version="1.0.0",
        trained_at="2026-10-01T12:00:00Z",
        training_samples_count=20,
        feature_names=EXPECTED_FEATURE_NAMES,
        hyperparameters={"n_estimators": 10},
    )


class TestModelManager:
    """Tests covering model serialization, deserialization, metadata validation, and error recovery."""

    def test_save_and_load_model_roundtrip(
        self,
        temp_models_dir: Path,
        dummy_model: IsolationForest,
        dummy_metadata: ModelMetadata,
    ) -> None:
        """Verify saving and subsequently loading a model and its companion metadata."""
        settings = load_config(models_dir=str(temp_models_dir))
        manager = ModelManager(settings=settings)

        artifact_path, meta_path = manager.save_model(
            model=dummy_model,
            metadata=dummy_metadata,
            prefix="test_model",
        )
        assert Path(artifact_path).exists()
        assert Path(meta_path).exists()

        loaded_model, loaded_meta = manager.load_model(artifact_path)
        assert isinstance(loaded_model, IsolationForest)
        assert loaded_meta.model_name == dummy_metadata.model_name
        assert loaded_meta.feature_names == EXPECTED_FEATURE_NAMES
        assert loaded_meta.training_samples_count == 20

    def test_load_latest_model(
        self,
        temp_models_dir: Path,
        dummy_model: IsolationForest,
        dummy_metadata: ModelMetadata,
    ) -> None:
        """Verify load_latest_model returns the newest valid checkpoint."""
        settings = load_config(models_dir=str(temp_models_dir))
        manager = ModelManager(settings=settings)

        # Before any save, load_latest_model returns None
        assert manager.load_latest_model() is None

        # Save first model
        manager.save_model(dummy_model, dummy_metadata, prefix="m1")

        loaded = manager.load_latest_model()
        assert loaded is not None
        model, meta = loaded
        assert meta.version == "1.0.0"

    def test_incompatible_schema_raises_error(
        self,
        temp_models_dir: Path,
        dummy_model: IsolationForest,
        dummy_metadata: ModelMetadata,
    ) -> None:
        """Verify that loading an artifact with altered or mismatched features raises IncompatibleModelError."""
        settings = load_config(models_dir=str(temp_models_dir))
        manager = ModelManager(settings=settings)

        # Save valid model first
        artifact_path, meta_path = manager.save_model(
            model=dummy_model,
            metadata=dummy_metadata,
            prefix="incompatible",
        )

        # Alter saved metadata on disk to omit a required feature
        corrupt_metadata = ModelMetadata(
            model_name="CorruptDetector",
            model_type="IsolationForest",
            version="1.0.0",
            trained_at="2026-10-01T12:00:00Z",
            training_samples_count=20,
            feature_names=EXPECTED_FEATURE_NAMES[:-1],  # Only 38 features
        )
        Path(meta_path).write_text(json.dumps(corrupt_metadata.to_dict()))

        with pytest.raises(IncompatibleModelError, match="Feature count mismatch"):
            manager.load_model(artifact_path)

    def test_missing_metadata_raises_error(
        self,
        temp_models_dir: Path,
        dummy_model: IsolationForest,
        dummy_metadata: ModelMetadata,
    ) -> None:
        """Verify that loading a model whose companion metadata JSON was deleted raises IncompatibleModelError."""
        settings = load_config(models_dir=str(temp_models_dir))
        manager = ModelManager(settings=settings)

        artifact_path, meta_path = manager.save_model(dummy_model, dummy_metadata)
        # Delete metadata file
        Path(meta_path).unlink()

        with pytest.raises(IncompatibleModelError, match="Missing companion metadata"):
            manager.load_model(artifact_path)

    def test_corrupted_model_file_raises_error(
        self,
        temp_models_dir: Path,
        dummy_metadata: ModelMetadata,
    ) -> None:
        """Verify that attempting to load a corrupt or unreadable joblib file raises ModelSerializationError."""
        settings = load_config(models_dir=str(temp_models_dir))
        manager = ModelManager(settings=settings)

        corrupt_artifact = temp_models_dir / "corrupt.joblib"
        corrupt_artifact.write_bytes(b"not a valid joblib pickle stream")

        meta_path = temp_models_dir / "corrupt.meta.json"
        meta_path.write_text(json.dumps(dummy_metadata.to_dict()))

        with pytest.raises(ModelSerializationError, match="Failed to deserialize model artifact"):
            manager.load_model(corrupt_artifact)

    def test_list_models(
        self,
        temp_models_dir: Path,
        dummy_model: IsolationForest,
        dummy_metadata: ModelMetadata,
    ) -> None:
        """Verify list_models enumerates existing checkpoints."""
        settings = load_config(models_dir=str(temp_models_dir))
        manager = ModelManager(settings=settings)

        assert len(manager.list_models()) == 0
        manager.save_model(dummy_model, dummy_metadata, prefix="mod_a")
        assert len(manager.list_models()) == 1
