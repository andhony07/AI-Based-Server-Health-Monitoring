"""Model artifact lifecycle management and safe serialization subsystem.

Provides atomic model persistence via joblib and companion JSON metadata validation
to prevent silent feature schema drift or corrupted model loads.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union

import joblib

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.ml.feature_schema import EXPECTED_FEATURE_NAMES, FEATURE_DIMENSION
from app.ml.models import ModelMetadata

logger = get_logger("app.ml.model_manager")


class ModelManagerError(Exception):
    """Base exception for model artifact lifecycle errors."""


class ModelNotFoundError(ModelManagerError):
    """Raised when an expected model artifact is missing from disk."""


class IncompatibleModelError(ModelManagerError):
    """Raised when loaded model artifact metadata is incompatible with current schema."""


class ModelSerializationError(ModelManagerError):
    """Raised when model serialization or deserialization fails."""


class ModelManager:
    """Manages saving, loading, and schema validation of trained ML models."""

    def __init__(
        self,
        models_dir: Optional[Union[Path, str]] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """Initialize the model manager.

        Args:
            models_dir: Directory where model artifacts and metadata reside. Defaults to settings.models_dir.
            settings: Application configuration settings container.
        """
        cfg = settings or get_settings()
        self.models_dir: Path = Path(models_dir or cfg.models_dir).resolve()
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, prefix: str = "isolation_forest") -> Path:
        """Return the filesystem path for the serialized estimator artifact."""
        return self.models_dir / f"{prefix}.joblib"

    def get_metadata_path(self, prefix: str = "isolation_forest") -> Path:
        """Return the filesystem path for the companion metadata JSON file."""
        return self.models_dir / f"{prefix}_metadata.json"

    def has_model(self, prefix: str = "isolation_forest") -> bool:
        """Check if both model checkpoint and companion metadata files exist on disk."""
        model_path = self.get_model_path(prefix)
        meta_path = self.get_metadata_path(prefix)
        alt_meta_path = self.models_dir / f"{prefix}.meta.json"
        return model_path.is_file() and (meta_path.is_file() or alt_meta_path.is_file())

    def get_metadata(self, prefix: str = "isolation_forest") -> Optional[ModelMetadata]:
        """Read and parse the model companion metadata without loading the heavy model binary.

        Args:
            prefix: Model file prefix.

        Returns:
            ModelMetadata instance if available and valid, None otherwise.
        """
        meta_path = self.get_metadata_path(prefix)
        if not meta_path.is_file():
            alt_meta_path = self.models_dir / f"{prefix}.meta.json"
            if alt_meta_path.is_file():
                meta_path = alt_meta_path
            else:
                return None

        try:
            content = meta_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return ModelMetadata.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to parse metadata from '%s': %s", meta_path, exc)
            return None

    def save_model(
        self,
        model: Any,
        metadata: ModelMetadata,
        prefix: str = "isolation_forest",
    ) -> tuple[Path, Path]:
        """Atomically persist a trained estimator binary and companion metadata JSON.

        Validates feature schema compatibility before writing. Writes to temporary
        files first to prevent corrupting existing working checkpoints on failure.

        Args:
            model: The trained scikit-learn estimator instance.
            metadata: ModelMetadata detailing training provenance and expected features.
            prefix: Artifact filename prefix.

        Returns:
            Tuple of (model_path, metadata_path).

        Raises:
            IncompatibleModelError: If metadata does not match current feature schema.
            ModelSerializationError: If serialization fails.
        """
        # Validate metadata feature consistency
        if len(metadata.feature_names) != FEATURE_DIMENSION:
            raise IncompatibleModelError(
                f"Feature count mismatch: {len(metadata.feature_names)} != {FEATURE_DIMENSION}"
            )
        if metadata.feature_names != EXPECTED_FEATURE_NAMES:
            raise IncompatibleModelError(
                f"Cannot save model: metadata feature names ({len(metadata.feature_names)}) "
                f"do not match system feature schema ({FEATURE_DIMENSION})."
            )

        model_path = self.get_model_path(prefix)
        meta_path = self.get_metadata_path(prefix)
        tmp_model = model_path.with_suffix(".tmp.joblib")
        tmp_meta = meta_path.with_suffix(".tmp.json")

        try:
            # 1. Serialize model binary to temp file
            joblib.dump(model, tmp_model, compress=3)

            # 2. Serialize metadata JSON to temp file
            meta_json = json.dumps(metadata.to_dict(), indent=2)
            tmp_meta.write_text(meta_json, encoding="utf-8")

            # 3. Atomic rename to production paths
            tmp_model.replace(model_path)
            tmp_meta.replace(meta_path)

            logger.info("Saved model artifact to '%s' with metadata '%s'.", model_path, meta_path)
            return model_path, meta_path

        except Exception as exc:
            if tmp_model.exists():
                tmp_model.unlink(missing_ok=True)
            if tmp_meta.exists():
                tmp_meta.unlink(missing_ok=True)
            logger.error("Failed to persist model '%s': %s", prefix, exc)
            raise ModelSerializationError(f"Failed to persist model '{prefix}': {exc}") from exc

    def load_model(
        self,
        target: Union[str, Path] = "isolation_forest",
    ) -> tuple[Any, ModelMetadata]:
        """Load and validate an active model checkpoint and its metadata.

        Strictly enforces feature compatibility with EXPECTED_FEATURE_NAMES (39 features).

        Args:
            target: Artifact filename prefix or direct filesystem Path to .joblib file.

        Returns:
            Tuple of (deserialized_model, ModelMetadata).

        Raises:
            ModelNotFoundError: If model files do not exist.
            IncompatibleModelError: If model features or schema version are incompatible.
            ModelSerializationError: If deserialization fails.
        """
        if isinstance(target, Path) or (isinstance(target, str) and target.endswith(".joblib")):
            model_path = Path(target)
            prefix = model_path.stem
            meta_path = model_path.parent / f"{prefix}_metadata.json"
            if not meta_path.is_file():
                meta_path = model_path.parent / f"{prefix}.meta.json"
        else:
            prefix = str(target)
            model_path = self.get_model_path(prefix)
            meta_path = self.get_metadata_path(prefix)
            if not meta_path.is_file():
                alt_meta_path = self.models_dir / f"{prefix}.meta.json"
                if alt_meta_path.is_file():
                    meta_path = alt_meta_path

        if not model_path.is_file():
            raise ModelNotFoundError(f"Model checkpoint not found at: '{model_path}'")
        if not meta_path.is_file():
            raise IncompatibleModelError(f"Missing companion metadata for: '{model_path}'")

        # 1. Inspect metadata first
        try:
            meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
            metadata = ModelMetadata.from_dict(meta_data)
        except Exception as exc:
            raise IncompatibleModelError(
                f"Model metadata at '{meta_path}' is corrupted or unreadable: {exc}"
            ) from exc

        # 2. Verify feature count and ordering
        if len(metadata.feature_names) != FEATURE_DIMENSION:
            raise IncompatibleModelError(
                f"Feature count mismatch: model has {len(metadata.feature_names)} features, "
                f"expected {FEATURE_DIMENSION}."
            )
        if metadata.feature_names != EXPECTED_FEATURE_NAMES:
            raise IncompatibleModelError(
                f"Model feature schema mismatch! Model was trained with features: "
                f"{metadata.feature_names[:3]}..., but system schema expects {EXPECTED_FEATURE_NAMES[:3]}..."
            )

        # 3. Load model binary
        try:
            model = joblib.load(model_path)
            logger.info("Loaded model '%s' (version %s) successfully.", prefix, metadata.version)
            return model, metadata
        except Exception as exc:
            logger.error("Failed to load model binary from '%s': %s", model_path, exc)
            raise ModelSerializationError(
                f"Failed to deserialize model artifact from '{model_path}': {exc}"
            ) from exc

    def load_latest_model(self) -> Optional[tuple[Any, ModelMetadata]]:
        """Find and load the newest valid model checkpoint in models_dir.

        Returns:
            Tuple of (model, metadata) if a valid checkpoint is found, None otherwise.
        """
        joblib_files = list(self.models_dir.glob("*.joblib"))
        if not joblib_files:
            return None

        # Sort by modification time descending
        joblib_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        for artifact in joblib_files:
            try:
                return self.load_model(artifact)
            except Exception as exc:
                logger.warning("Skipping incompatible or invalid checkpoint '%s': %s", artifact, exc)

        return None

    def list_models(self) -> list[str]:
        """List all valid model names present in models_dir.

        Returns:
            List of model stem names.
        """
        valid_models = []
        for artifact in self.models_dir.glob("*.joblib"):
            prefix = artifact.stem
            meta_1 = self.models_dir / f"{prefix}_metadata.json"
            meta_2 = self.models_dir / f"{prefix}.meta.json"
            if meta_1.is_file() or meta_2.is_file():
                valid_models.append(prefix)
        return sorted(valid_models)

