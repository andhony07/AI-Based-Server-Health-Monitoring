"""Schema migration management subsystem.

Handles idempotent schema initialization, version tracking, and schema evolution
for the server health monitoring database.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Callable, Final

from app.core.logging_config import get_logger
from app.database.connection import DatabaseMigrationError, transaction_scope
from app.database.schema import (
    CREATE_FEATURE_VECTORS_TABLE,
    CREATE_INDEXES_SQL,
    CREATE_SCHEMA_MIGRATIONS_TABLE,
    CREATE_SYSTEM_METRICS_TABLE,
    CREATE_VALIDATION_LOGS_TABLE,
    SCHEMA_VERSION,
)

logger = get_logger("app.database.migrations")


def get_current_schema_version(conn: sqlite3.Connection) -> int:
    """Retrieve the latest schema version applied to the database.

    Args:
        conn: Active sqlite3.Connection.

    Returns:
        Current version integer, or 0 if no migrations have been applied.
    """
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations';"
        )
        if not cursor.fetchone():
            return 0

        cursor = conn.execute(
            "SELECT MAX(version) AS max_version FROM schema_migrations;"
        )
        row = cursor.fetchone()
        if row and row["max_version"] is not None:
            return int(row["max_version"])
        return 0
    except sqlite3.Error as err:
        logger.error("Failed to query schema_migrations table: %s", err)
        return 0


def _migration_v1(conn: sqlite3.Connection) -> None:
    """Apply version 1 migration: initial telemetry, feature, and validation schema."""
    conn.execute(CREATE_SCHEMA_MIGRATIONS_TABLE)
    conn.execute(CREATE_SYSTEM_METRICS_TABLE)
    conn.execute(CREATE_FEATURE_VECTORS_TABLE)
    conn.execute(CREATE_VALIDATION_LOGS_TABLE)
    for index_stmt in CREATE_INDEXES_SQL:
        conn.execute(index_stmt)


# Ordered registry of schema migration actions
MIGRATIONS: Final[dict[int, tuple[str, Callable[[sqlite3.Connection], None]]]] = {
    1: ("Initial telemetry, feature vectors, and validation audit tables", _migration_v1),
}


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Apply any pending schema migrations up to the target SCHEMA_VERSION.

    This operation is fully idempotent: running it repeatedly on an up-to-date
    database is a fast no-op that will not alter or destroy existing data.

    Args:
        conn: Active sqlite3.Connection.

    Returns:
        The highest schema version now present in the database.

    Raises:
        DatabaseMigrationError: If executing any migration step fails.
    """
    try:
        # Ensure schema_migrations table exists
        conn.execute(CREATE_SCHEMA_MIGRATIONS_TABLE)
        current_version = get_current_schema_version(conn)

        if current_version >= SCHEMA_VERSION:
            logger.debug(
                "Database schema is up to date at version %d (latest: %d).",
                current_version,
                SCHEMA_VERSION,
            )
            return current_version

        logger.info(
            "Migrating database schema from version %d to %d...",
            current_version,
            SCHEMA_VERSION,
        )

        for version, (description, migration_fn) in sorted(MIGRATIONS.items()):
            if version > current_version:
                logger.info("Applying migration v%d: %s", version, description)
                with transaction_scope(conn):
                    migration_fn(conn)
                    conn.execute(
                        """
                        INSERT INTO schema_migrations (version, applied_at, description)
                        VALUES (?, ?, ?);
                        """,
                        (
                            version,
                            datetime.now(timezone.utc).isoformat(),
                            description,
                        ),
                    )
                logger.info("Migration v%d applied successfully.", version)

        return SCHEMA_VERSION

    except Exception as exc:
        logger.error("Database migration failed: %s", exc)
        raise DatabaseMigrationError(f"Database migration failed: {exc}") from exc
