"""Database schema definitions, column constants, and index declarations.

Defines the relational tables for raw system metrics, 39-feature vectors,
validation audit logs, and versioned schema migrations.
"""

from __future__ import annotations

from typing import Final

SCHEMA_VERSION: Final[int] = 1

FEATURE_COLUMNS: Final[tuple[str, ...]] = (
    # CPU Features (6)
    "cpu_utilization_percent",
    "cpu_utilization_delta",
    "cpu_utilization_rolling_mean",
    "cpu_utilization_rolling_max",
    "cpu_utilization_rolling_min",
    "cpu_cores_logical",
    # Memory Features (7)
    "memory_utilization_percent",
    "memory_used_mb",
    "memory_available_mb",
    "memory_utilization_delta",
    "memory_used_delta_mb",
    "memory_utilization_rolling_mean",
    "memory_utilization_rolling_max",
    # Disk Features (5)
    "disk_utilization_percent",
    "disk_used_gb",
    "disk_free_gb",
    "disk_utilization_delta",
    "disk_utilization_rolling_mean",
    # Network Features (8)
    "network_bytes_sent_per_sec",
    "network_bytes_recv_per_sec",
    "network_sent_delta_per_sec",
    "network_recv_delta_per_sec",
    "network_bytes_sent_rolling_mean",
    "network_bytes_recv_rolling_mean",
    "network_bytes_sent_rolling_max",
    "network_bytes_recv_rolling_max",
    # Process Features (5)
    "process_count",
    "top_process_cpu_percent",
    "top_process_memory_percent",
    "top_processes_total_cpu_percent",
    "top_processes_total_memory_percent",
    # Temporal Features (3)
    "sample_interval_sec",
    "hour_of_day",
    "day_of_week",
    # Quality / Missing Indicators (5)
    "is_cpu_missing",
    "is_memory_missing",
    "is_disk_missing",
    "is_network_missing",
    "is_processes_missing",
)

# Table DDL statements
CREATE_SCHEMA_MIGRATIONS_TABLE: Final[str] = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
);
"""

CREATE_SYSTEM_METRICS_TABLE: Final[str] = """
CREATE TABLE IF NOT EXISTS system_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    cpu_percent REAL,
    cpu_logical_cores INTEGER,
    cpu_physical_cores INTEGER,
    memory_total_bytes INTEGER,
    memory_used_bytes INTEGER,
    memory_available_bytes INTEGER,
    memory_percent REAL,
    disk_total_bytes INTEGER,
    disk_used_bytes INTEGER,
    disk_free_bytes INTEGER,
    disk_percent REAL,
    network_bytes_sent INTEGER,
    network_bytes_recv INTEGER,
    network_bytes_sent_per_sec REAL,
    network_bytes_recv_per_sec REAL,
    process_count INTEGER,
    top_process_pid INTEGER,
    top_process_name TEXT,
    top_process_cpu_percent REAL,
    top_process_memory_percent REAL,
    raw_payload_json TEXT NOT NULL
);
"""

# Dynamically construct feature vectors table with all 39 numerical feature columns
_feature_cols_sql = ",\n    ".join(f"{col} REAL NOT NULL" for col in FEATURE_COLUMNS)

CREATE_FEATURE_VECTORS_TABLE: Final[str] = f"""
CREATE TABLE IF NOT EXISTS feature_vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER,
    timestamp TEXT NOT NULL,
    {_feature_cols_sql},
    features_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    FOREIGN KEY (metric_id) REFERENCES system_metrics(id) ON DELETE CASCADE
);
"""

CREATE_VALIDATION_LOGS_TABLE: Final[str] = """
CREATE TABLE IF NOT EXISTS validation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER,
    timestamp TEXT NOT NULL,
    is_valid INTEGER NOT NULL,
    issues_count INTEGER NOT NULL,
    has_errors INTEGER NOT NULL,
    issues_json TEXT NOT NULL,
    FOREIGN KEY (metric_id) REFERENCES system_metrics(id) ON DELETE CASCADE
);
"""

# Index declarations for fast timestamp-based and foreign-key queries
CREATE_INDEXES_SQL: Final[list[str]] = [
    "CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_feature_vectors_timestamp ON feature_vectors(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_feature_vectors_metric_id ON feature_vectors(metric_id);",
    "CREATE INDEX IF NOT EXISTS idx_validation_logs_timestamp ON validation_logs(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_validation_logs_metric_id ON validation_logs(metric_id);",
]
