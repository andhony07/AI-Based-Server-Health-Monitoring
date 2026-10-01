"""Database storage and persistence layer.

Provides SQLite connection lifecycle, versioned migrations, relational tables
for raw telemetry, 39-feature vectors, validation audit logs, and atomic transactional persistence.
"""

from __future__ import annotations

from app.database.connection import (
    DatabaseConnectionError,
    DatabaseError,
    DatabaseMigrationError,
    DatabaseTransactionError,
    create_connection,
    db_session,
    get_connection,
    transaction_scope,
)
from app.database.migrations import apply_migrations, get_current_schema_version
from app.database.models import (
    FeatureVectorRecord,
    PersistenceResult,
    SystemMetricRecord,
    ValidationLogRecord,
)
from app.database.repository import MetricsRepository
from app.database.schema import FEATURE_COLUMNS, SCHEMA_VERSION
from app.database.service import PersistenceService

__all__: list[str] = [
    "DatabaseConnectionError",
    "DatabaseError",
    "DatabaseMigrationError",
    "DatabaseTransactionError",
    "FEATURE_COLUMNS",
    "FeatureVectorRecord",
    "MetricsRepository",
    "PersistenceResult",
    "PersistenceService",
    "SCHEMA_VERSION",
    "SystemMetricRecord",
    "ValidationLogRecord",
    "apply_migrations",
    "create_connection",
    "db_session",
    "get_connection",
    "get_current_schema_version",
    "transaction_scope",
]
