"""Repository layer for database operations on telemetry, features, and validation logs.

Provides parameterized queries, type-safe entity mapping, range retrieval,
record counting, and data retention deletion.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Final, Optional

from app.core.logging_config import get_logger
from app.database.models import (
    FeatureVectorRecord,
    SystemMetricRecord,
    ValidationLogRecord,
    parse_utc_timestamp,
)
from app.database.schema import FEATURE_COLUMNS
from app.models.metrics import SystemMetrics
from app.preprocessing.feature_engineer import FeatureVector
from app.preprocessing.validator import ValidationResult

logger = get_logger("app.database.repository")

ALLOWED_TABLES: Final[set[str]] = {
    "system_metrics",
    "feature_vectors",
    "validation_logs",
    "schema_migrations",
}


class MetricsRepository:
    """Encapsulates all SQL CRUD operations for system health monitoring data."""

    def __init__(self) -> None:
        """Initialize the repository."""

    # -------------------------------------------------------------------------
    # System Metrics (Raw Telemetry) Operations
    # -------------------------------------------------------------------------

    def insert_system_metrics(
        self,
        conn: sqlite3.Connection,
        metrics: SystemMetrics,
    ) -> int:
        """Insert a raw SystemMetrics snapshot into the system_metrics table.

        Args:
            conn: Active sqlite3.Connection.
            metrics: Populated SystemMetrics instance.

        Returns:
            The generated primary key row id.
        """
        top_process = None
        if metrics.processes:
            top_process = max(metrics.processes, key=lambda p: p.cpu_percent)

        raw_payload = json.dumps(metrics.to_dict())

        query = """
        INSERT INTO system_metrics (
            timestamp,
            cpu_percent,
            cpu_logical_cores,
            cpu_physical_cores,
            memory_total_bytes,
            memory_used_bytes,
            memory_available_bytes,
            memory_percent,
            disk_total_bytes,
            disk_used_bytes,
            disk_free_bytes,
            disk_percent,
            network_bytes_sent,
            network_bytes_recv,
            network_bytes_sent_per_sec,
            network_bytes_recv_per_sec,
            process_count,
            top_process_pid,
            top_process_name,
            top_process_cpu_percent,
            top_process_memory_percent,
            raw_payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        params = (
            metrics.timestamp.isoformat(),
            metrics.cpu.utilization_percent if metrics.cpu else None,
            metrics.cpu.logical_cores if metrics.cpu else None,
            metrics.cpu.physical_cores if metrics.cpu else None,
            metrics.memory.total_bytes if metrics.memory else None,
            metrics.memory.used_bytes if metrics.memory else None,
            metrics.memory.available_bytes if metrics.memory else None,
            metrics.memory.utilization_percent if metrics.memory else None,
            metrics.disk.total_bytes if metrics.disk else None,
            metrics.disk.used_bytes if metrics.disk else None,
            metrics.disk.free_bytes if metrics.disk else None,
            metrics.disk.utilization_percent if metrics.disk else None,
            metrics.network.bytes_sent if metrics.network else None,
            metrics.network.bytes_recv if metrics.network else None,
            metrics.network.bytes_sent_per_sec if metrics.network else None,
            metrics.network.bytes_recv_per_sec if metrics.network else None,
            len(metrics.processes),
            top_process.pid if top_process else None,
            top_process.name if top_process else None,
            top_process.cpu_percent if top_process else None,
            top_process.memory_percent if top_process else None,
            raw_payload,
        )

        cursor = conn.execute(query, params)
        metric_id = cursor.lastrowid
        if metric_id is None:
            raise sqlite3.OperationalError("Failed to retrieve lastrowid for system_metrics insert.")
        return int(metric_id)

    def get_system_metrics_by_id(
        self,
        conn: sqlite3.Connection,
        metric_id: int,
    ) -> Optional[SystemMetricRecord]:
        """Fetch a single system_metrics record by primary key id.

        Args:
            conn: Active sqlite3.Connection.
            metric_id: Primary key ID to retrieve.

        Returns:
            SystemMetricRecord if found, else None.
        """
        cursor = conn.execute(
            "SELECT * FROM system_metrics WHERE id = ?;",
            (metric_id,),
        )
        row = cursor.fetchone()
        return self._map_row_to_system_metric(row) if row else None

    def get_latest_system_metrics(
        self,
        conn: sqlite3.Connection,
        limit: int = 10,
    ) -> list[SystemMetricRecord]:
        """Fetch the most recent system metrics ordered by timestamp descending.

        Args:
            conn: Active sqlite3.Connection.
            limit: Maximum number of rows to return.

        Returns:
            List of SystemMetricRecord instances.
        """
        cursor = conn.execute(
            "SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT ?;",
            (max(1, limit),),
        )
        return [self._map_row_to_system_metric(row) for row in cursor.fetchall()]

    def get_system_metrics_range(
        self,
        conn: sqlite3.Connection,
        start_time: datetime,
        end_time: datetime,
    ) -> list[SystemMetricRecord]:
        """Fetch system metrics records within an inclusive timestamp range.

        Args:
            conn: Active sqlite3.Connection.
            start_time: Range start timestamp (UTC).
            end_time: Range end timestamp (UTC).

        Returns:
            List of SystemMetricRecord instances ordered chronologically.
        """
        cursor = conn.execute(
            """
            SELECT * FROM system_metrics
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC;
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )
        return [self._map_row_to_system_metric(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Feature Vectors Operations
    # -------------------------------------------------------------------------

    def insert_feature_vector(
        self,
        conn: sqlite3.Connection,
        vector: FeatureVector,
        metric_id: Optional[int] = None,
    ) -> int:
        """Insert an engineered FeatureVector into the feature_vectors table.

        Args:
            conn: Active sqlite3.Connection.
            vector: Populated FeatureVector containing 39 features.
            metric_id: Optional associated system_metrics record ID.

        Returns:
            The generated primary key row id.
        """
        cols = ["metric_id", "timestamp"] + list(FEATURE_COLUMNS) + ["features_json", "metadata_json"]
        placeholders = ", ".join(["?"] * len(cols))
        cols_sql = ", ".join(cols)

        feature_values = [vector.get(col, 0.0) for col in FEATURE_COLUMNS]
        features_json = json.dumps(vector.features)
        metadata_json = json.dumps(vector.metadata)

        params: list[Any] = [metric_id, vector.timestamp.isoformat()]
        params.extend(feature_values)
        params.extend([features_json, metadata_json])

        query = f"INSERT INTO feature_vectors ({cols_sql}) VALUES ({placeholders});"
        cursor = conn.execute(query, params)
        feature_id = cursor.lastrowid
        if feature_id is None:
            raise sqlite3.OperationalError("Failed to retrieve lastrowid for feature_vectors insert.")
        return int(feature_id)

    def get_feature_vector_by_id(
        self,
        conn: sqlite3.Connection,
        vector_id: int,
    ) -> Optional[FeatureVectorRecord]:
        """Fetch a feature vector record by primary key id.

        Args:
            conn: Active sqlite3.Connection.
            vector_id: Primary key ID to retrieve.

        Returns:
            FeatureVectorRecord if found, else None.
        """
        cursor = conn.execute(
            "SELECT * FROM feature_vectors WHERE id = ?;",
            (vector_id,),
        )
        row = cursor.fetchone()
        return self._map_row_to_feature_vector(row) if row else None

    def get_latest_feature_vectors(
        self,
        conn: sqlite3.Connection,
        limit: int = 10,
    ) -> list[FeatureVectorRecord]:
        """Fetch the most recent feature vectors ordered by timestamp descending.

        Args:
            conn: Active sqlite3.Connection.
            limit: Maximum number of rows to return.

        Returns:
            List of FeatureVectorRecord instances.
        """
        cursor = conn.execute(
            "SELECT * FROM feature_vectors ORDER BY timestamp DESC LIMIT ?;",
            (max(1, limit),),
        )
        return [self._map_row_to_feature_vector(row) for row in cursor.fetchall()]

    def get_feature_vectors_range(
        self,
        conn: sqlite3.Connection,
        start_time: datetime,
        end_time: datetime,
    ) -> list[FeatureVectorRecord]:
        """Fetch feature vector records within a timestamp range.

        Args:
            conn: Active sqlite3.Connection.
            start_time: Range start timestamp (UTC).
            end_time: Range end timestamp (UTC).

        Returns:
            List of FeatureVectorRecord instances ordered chronologically.
        """
        cursor = conn.execute(
            """
            SELECT * FROM feature_vectors
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC;
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )
        return [self._map_row_to_feature_vector(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Validation Logs Operations
    # -------------------------------------------------------------------------

    def insert_validation_log(
        self,
        conn: sqlite3.Connection,
        validation: ValidationResult,
        timestamp: datetime,
        metric_id: Optional[int] = None,
    ) -> int:
        """Insert a preprocessing validation report into validation_logs table.

        Args:
            conn: Active sqlite3.Connection.
            validation: ValidationResult produced by MetricsValidator.
            timestamp: Sample timestamp (UTC).
            metric_id: Optional associated system_metrics record ID.

        Returns:
            The generated primary key row id.
        """
        issues_serializable = [
            {
                "domain": issue.domain,
                "field_name": issue.field_name,
                "issue_type": issue.issue_type,
                "message": issue.message,
                "value": str(issue.value) if issue.value is not None else None,
                "severity": issue.severity,
            }
            for issue in validation.issues
        ]

        query = """
        INSERT INTO validation_logs (
            metric_id,
            timestamp,
            is_valid,
            issues_count,
            has_errors,
            issues_json
        ) VALUES (?, ?, ?, ?, ?, ?);
        """

        params = (
            metric_id,
            timestamp.isoformat(),
            1 if validation.is_valid else 0,
            len(validation.issues),
            1 if validation.has_errors else 0,
            json.dumps(issues_serializable),
        )

        cursor = conn.execute(query, params)
        log_id = cursor.lastrowid
        if log_id is None:
            raise sqlite3.OperationalError("Failed to retrieve lastrowid for validation_logs insert.")
        return int(log_id)

    def get_validation_log_by_id(
        self,
        conn: sqlite3.Connection,
        log_id: int,
    ) -> Optional[ValidationLogRecord]:
        """Fetch a validation log record by primary key id.

        Args:
            conn: Active sqlite3.Connection.
            log_id: Primary key ID to retrieve.

        Returns:
            ValidationLogRecord if found, else None.
        """
        cursor = conn.execute(
            "SELECT * FROM validation_logs WHERE id = ?;",
            (log_id,),
        )
        row = cursor.fetchone()
        return self._map_row_to_validation_log(row) if row else None

    def get_latest_validation_logs(
        self,
        conn: sqlite3.Connection,
        limit: int = 10,
    ) -> list[ValidationLogRecord]:
        """Fetch the most recent validation logs ordered by timestamp descending.

        Args:
            conn: Active sqlite3.Connection.
            limit: Maximum number of rows to return.

        Returns:
            List of ValidationLogRecord instances.
        """
        cursor = conn.execute(
            "SELECT * FROM validation_logs ORDER BY timestamp DESC LIMIT ?;",
            (max(1, limit),),
        )
        return [self._map_row_to_validation_log(row) for row in cursor.fetchall()]

    def get_validation_logs_range(
        self,
        conn: sqlite3.Connection,
        start_time: datetime,
        end_time: datetime,
    ) -> list[ValidationLogRecord]:
        """Fetch validation logs within a timestamp range.

        Args:
            conn: Active sqlite3.Connection.
            start_time: Range start timestamp (UTC).
            end_time: Range end timestamp (UTC).

        Returns:
            List of ValidationLogRecord instances ordered chronologically.
        """
        cursor = conn.execute(
            """
            SELECT * FROM validation_logs
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC;
            """,
            (start_time.isoformat(), end_time.isoformat()),
        )
        return [self._map_row_to_validation_log(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Maintenance & Retention Operations
    # -------------------------------------------------------------------------

    def count_records(self, conn: sqlite3.Connection, table_name: str) -> int:
        """Count total rows in a specific table safely using a strict table whitelist.

        Args:
            conn: Active sqlite3.Connection.
            table_name: One of the allowed table identifiers.

        Returns:
            Integer row count.

        Raises:
            ValueError: If table_name is not in the allowed table whitelist.
        """
        if table_name not in ALLOWED_TABLES:
            raise ValueError(
                f"Unauthorized table name '{table_name}'. Must be one of: {ALLOWED_TABLES}"
            )
        cursor = conn.execute(f"SELECT COUNT(*) AS total FROM {table_name};")  # noqa: S608
        row = cursor.fetchone()
        return int(row["total"]) if row else 0

    def count_all_records(self, conn: sqlite3.Connection) -> dict[str, int]:
        """Return total row counts across all managed persistence tables.

        Args:
            conn: Active sqlite3.Connection.

        Returns:
            Mapping of table name to row count.
        """
        return {
            table: self.count_records(conn, table)
            for table in sorted(ALLOWED_TABLES)
        }

    def delete_records_older_than(
        self,
        conn: sqlite3.Connection,
        cutoff_time: datetime,
    ) -> dict[str, int]:
        """Delete historical records older than a specified cutoff timestamp.

        Cascades from system_metrics through foreign keys to feature_vectors
        and validation_logs. Also safely purges unlinked rows if any exist.

        Args:
            conn: Active sqlite3.Connection inside a transaction.
            cutoff_time: Datetime threshold (UTC). Records before this will be deleted.

        Returns:
            Dictionary with counts of deleted records per table.
        """
        cutoff_iso = cutoff_time.isoformat()

        # Delete from validation_logs (matching timestamp or linked to expired metric)
        cur_val = conn.execute(
            """
            DELETE FROM validation_logs
            WHERE timestamp < ? OR metric_id IN (
                SELECT id FROM system_metrics WHERE timestamp < ?
            );
            """,
            (cutoff_iso, cutoff_iso),
        )
        val_deleted = cur_val.rowcount

        # Delete from feature_vectors (matching timestamp or linked to expired metric)
        cur_feat = conn.execute(
            """
            DELETE FROM feature_vectors
            WHERE timestamp < ? OR metric_id IN (
                SELECT id FROM system_metrics WHERE timestamp < ?
            );
            """,
            (cutoff_iso, cutoff_iso),
        )
        feat_deleted = cur_feat.rowcount

        # Delete from system_metrics
        cur_metrics = conn.execute(
            "DELETE FROM system_metrics WHERE timestamp < ?;",
            (cutoff_iso,),
        )
        metrics_deleted = cur_metrics.rowcount

        return {
            "system_metrics": max(0, metrics_deleted),
            "feature_vectors": max(0, feat_deleted),
            "validation_logs": max(0, val_deleted),
        }

    # -------------------------------------------------------------------------
    # Internal Row Mapping Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _map_row_to_system_metric(row: sqlite3.Row) -> SystemMetricRecord:
        """Map a sqlite3.Row from system_metrics to SystemMetricRecord."""
        raw_payload = {}
        if row["raw_payload_json"]:
            try:
                raw_payload = json.loads(row["raw_payload_json"])
            except (json.JSONDecodeError, TypeError):
                raw_payload = {}

        return SystemMetricRecord(
            id=int(row["id"]),
            timestamp=parse_utc_timestamp(row["timestamp"]),
            cpu_percent=row["cpu_percent"],
            cpu_logical_cores=row["cpu_logical_cores"],
            cpu_physical_cores=row["cpu_physical_cores"],
            memory_total_bytes=row["memory_total_bytes"],
            memory_used_bytes=row["memory_used_bytes"],
            memory_available_bytes=row["memory_available_bytes"],
            memory_percent=row["memory_percent"],
            disk_total_bytes=row["disk_total_bytes"],
            disk_used_bytes=row["disk_used_bytes"],
            disk_free_bytes=row["disk_free_bytes"],
            disk_percent=row["disk_percent"],
            network_bytes_sent=row["network_bytes_sent"],
            network_bytes_recv=row["network_bytes_recv"],
            network_bytes_sent_per_sec=row["network_bytes_sent_per_sec"],
            network_bytes_recv_per_sec=row["network_bytes_recv_per_sec"],
            process_count=row["process_count"],
            top_process_pid=row["top_process_pid"],
            top_process_name=row["top_process_name"],
            top_process_cpu_percent=row["top_process_cpu_percent"],
            top_process_memory_percent=row["top_process_memory_percent"],
            raw_payload=raw_payload,
        )

    @staticmethod
    def _map_row_to_feature_vector(row: sqlite3.Row) -> FeatureVectorRecord:
        """Map a sqlite3.Row from feature_vectors to FeatureVectorRecord."""
        features: dict[str, float] = {}
        if "features_json" in row.keys() and row["features_json"]:
            try:
                features = json.loads(row["features_json"])
            except (json.JSONDecodeError, TypeError):
                features = {col: float(row[col]) for col in FEATURE_COLUMNS if col in row.keys()}
        else:
            features = {col: float(row[col]) for col in FEATURE_COLUMNS if col in row.keys()}

        metadata = {}
        if "metadata_json" in row.keys() and row["metadata_json"]:
            try:
                metadata = json.loads(row["metadata_json"])
            except (json.JSONDecodeError, TypeError):
                metadata = {}

        return FeatureVectorRecord(
            id=int(row["id"]),
            metric_id=int(row["metric_id"]) if row["metric_id"] is not None else None,
            timestamp=parse_utc_timestamp(row["timestamp"]),
            features=features,
            metadata=metadata,
        )

    @staticmethod
    def _map_row_to_validation_log(row: sqlite3.Row) -> ValidationLogRecord:
        """Map a sqlite3.Row from validation_logs to ValidationLogRecord."""
        issues = []
        if row["issues_json"]:
            try:
                issues = json.loads(row["issues_json"])
            except (json.JSONDecodeError, TypeError):
                issues = []

        return ValidationLogRecord(
            id=int(row["id"]),
            metric_id=int(row["metric_id"]) if row["metric_id"] is not None else None,
            timestamp=parse_utc_timestamp(row["timestamp"]),
            is_valid=bool(row["is_valid"]),
            issues_count=int(row["issues_count"]),
            has_errors=bool(row["has_errors"]),
            issues=issues,
        )
