"""Persistence service coordinator for system telemetry data storage.

Coordinates atomic multi-table persistence across raw telemetry, engineered
feature vectors, and validation audit logs with safe error handling and retention management.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Union

from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.database.connection import db_session, get_connection
from app.database.migrations import apply_migrations
from app.database.models import (
    FeatureVectorRecord,
    PersistenceResult,
    SystemMetricRecord,
    ValidationLogRecord,
)
from app.database.repository import MetricsRepository
from app.models.metrics import SystemMetrics
from app.preprocessing.pipeline import ProcessedTelemetry

logger = get_logger("app.database.service")


class PersistenceService:
    """Coordinates high-level database operations, transactions, and retention cleanup."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        repository: Optional[MetricsRepository] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> None:
        """Initialize the persistence service.

        Args:
            settings: Application configuration settings container.
            repository: Custom MetricsRepository instance.
            db_path: Optional explicit database path override.
        """
        self.settings: Settings = settings or get_settings()
        self.db_path: Path = Path(db_path or self.settings.database_path).resolve()
        self.repository: MetricsRepository = repository or MetricsRepository()
        self._timeout: float = self.settings.db_connection_timeout

        if self.settings.db_auto_init:
            self.initialize_database()

    def initialize_database(self) -> bool:
        """Initialize the database schema idempotently.

        Creates parent directory layout and applies any pending migrations.

        Returns:
            True if schema is successfully verified/migrated, False on failure.
        """
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with get_connection(self.db_path, timeout=self._timeout) as conn:
                version = apply_migrations(conn)
                logger.info(
                    "SQLite persistence database ready at '%s' (schema v%d).",
                    self.db_path,
                    version,
                )
            return True
        except Exception as exc:
            logger.error("Database initialization failed for '%s': %s", self.db_path, exc)
            return False

    def persist_sample(
        self,
        metrics: SystemMetrics,
        processed: ProcessedTelemetry,
    ) -> PersistenceResult:
        """Atomically persist a complete monitoring sample into the database.

        Transactions ensure that either ALL three linked records (raw metrics,
        feature vector, and validation log) are safely committed, or NONE are.

        Args:
            metrics: Raw SystemMetrics snapshot from Phase 2.
            processed: ProcessedTelemetry output containing FeatureVector and ValidationResult.

        Returns:
            PersistenceResult detailing success status and generated primary keys.
        """
        try:
            with db_session(self.db_path, timeout=self._timeout) as session:
                # 1. Insert raw telemetry
                metric_id = self.repository.insert_system_metrics(
                    conn=session,
                    metrics=metrics,
                )

                # 2. Insert engineered 39-feature vector linked to metric_id
                feature_id = self.repository.insert_feature_vector(
                    conn=session,
                    vector=processed.feature_vector,
                    metric_id=metric_id,
                )

                # 3. Insert validation audit logs linked to metric_id
                validation_id = self.repository.insert_validation_log(
                    conn=session,
                    validation=processed.validation_result,
                    timestamp=metrics.timestamp,
                    metric_id=metric_id,
                )

            logger.debug(
                "Persisted sample #%d (feature_id=%d, validation_id=%d, valid=%s)",
                metric_id,
                feature_id,
                validation_id,
                processed.validation_result.is_valid,
            )

            return PersistenceResult(
                success=True,
                metric_id=metric_id,
                feature_id=feature_id,
                validation_id=validation_id,
            )

        except Exception as exc:
            logger.error("Failed to persist telemetry sample: %s", exc)
            return PersistenceResult(
                success=False,
                error_message=str(exc),
            )

    def apply_retention_policy(
        self,
        retention_days: Optional[int] = None,
    ) -> dict[str, int]:
        """Purge historical telemetry older than the configured retention threshold.

        Args:
            retention_days: Threshold in days. If None, checks settings.db_retention_days.

        Returns:
            Dictionary detailing number of purged records per table.
        """
        effective_days = (
            retention_days
            if retention_days is not None
            else self.settings.db_retention_days
        )

        if effective_days is None or effective_days <= 0:
            logger.debug("Retention policy inactive (db_retention_days is unset).")
            return {"system_metrics": 0, "feature_vectors": 0, "validation_logs": 0}

        cutoff = datetime.now(timezone.utc) - timedelta(days=effective_days)
        logger.info(
            "Executing retention cleanup for records older than %d days (cutoff: %s)...",
            effective_days,
            cutoff.isoformat(),
        )

        try:
            with db_session(self.db_path, timeout=self._timeout) as session:
                deleted = self.repository.delete_records_older_than(session, cutoff)

            logger.info("Retention cleanup completed: %s", deleted)
            return deleted
        except Exception as exc:
            logger.error("Retention purge failed: %s", exc)
            return {"system_metrics": 0, "feature_vectors": 0, "validation_logs": 0}

    # -------------------------------------------------------------------------
    # Convenience Query Methods
    # -------------------------------------------------------------------------

    def get_latest_metrics(self, limit: int = 10) -> list[SystemMetricRecord]:
        """Retrieve the most recent raw system metric snapshots.

        Args:
            limit: Maximum count to return.

        Returns:
            List of SystemMetricRecord instances.
        """
        with get_connection(self.db_path, timeout=self._timeout) as conn:
            return self.repository.get_latest_system_metrics(conn, limit=limit)

    def get_latest_features(self, limit: int = 10) -> list[FeatureVectorRecord]:
        """Retrieve the most recent engineered feature vectors.

        Args:
            limit: Maximum count to return.

        Returns:
            List of FeatureVectorRecord instances.
        """
        with get_connection(self.db_path, timeout=self._timeout) as conn:
            return self.repository.get_latest_feature_vectors(conn, limit=limit)

    def get_latest_validation_logs(self, limit: int = 10) -> list[ValidationLogRecord]:
        """Retrieve the most recent validation audit logs.

        Args:
            limit: Maximum count to return.

        Returns:
            List of ValidationLogRecord instances.
        """
        with get_connection(self.db_path, timeout=self._timeout) as conn:
            return self.repository.get_latest_validation_logs(conn, limit=limit)

    def get_metrics_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[SystemMetricRecord]:
        """Retrieve raw telemetry between two timestamps.

        Args:
            start_time: Earliest timestamp (UTC).
            end_time: Latest timestamp (UTC).

        Returns:
            Chronologically sorted list of SystemMetricRecord instances.
        """
        with get_connection(self.db_path, timeout=self._timeout) as conn:
            return self.repository.get_system_metrics_range(conn, start_time, end_time)

    def get_features_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[FeatureVectorRecord]:
        """Retrieve engineered feature vectors between two timestamps.

        Args:
            start_time: Earliest timestamp (UTC).
            end_time: Latest timestamp (UTC).

        Returns:
            Chronologically sorted list of FeatureVectorRecord instances.
        """
        with get_connection(self.db_path, timeout=self._timeout) as conn:
            return self.repository.get_feature_vectors_range(conn, start_time, end_time)

    def get_record_counts(self) -> dict[str, int]:
        """Return total row counts for all managed tables.

        Returns:
            Dictionary mapping table name to row count.
        """
        with get_connection(self.db_path, timeout=self._timeout) as conn:
            return self.repository.count_all_records(conn)

    def close(self) -> None:
        """Close or flush any persistent database resources if needed."""
        logger.debug("Database persistence service closed.")
