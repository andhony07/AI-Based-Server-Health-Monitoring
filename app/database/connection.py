"""Database connection and transaction management subsystem.

Provides robust SQLite connection lifecycle management, transaction scopes,
WAL mode configuration, foreign key enforcement, and explicit error handling.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Union

from app.core.logging_config import get_logger

logger = get_logger("app.database.connection")


class DatabaseError(Exception):
    """Base exception for all database-related operations."""


class DatabaseConnectionError(DatabaseError):
    """Raised when establishing a connection to the database fails."""


class DatabaseTransactionError(DatabaseError):
    """Raised when a transactional block fails and cannot be committed."""


class DatabaseMigrationError(DatabaseError):
    """Raised when a schema migration fails to execute."""


def create_connection(
    db_path: Union[Path, str],
    timeout: float = 30.0,
) -> sqlite3.Connection:
    """Establish and configure a connection to the SQLite database.

    Enables WAL mode, enforces foreign keys, sets busy timeouts,
    and configures sqlite3.Row for dict-like row access.

    Args:
        db_path: Filesystem path to the SQLite database file.
        timeout: Maximum seconds to wait when acquiring a lock.

    Returns:
        Configured sqlite3.Connection instance.

    Raises:
        DatabaseConnectionError: If connection or PRAGMA initialization fails.
    """
    path_obj = Path(db_path).resolve()
    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(path_obj),
            timeout=timeout,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode; explicit BEGIN for transactions
        )
        conn.row_factory = sqlite3.Row

        # SQLite performance and integrity PRAGMAs
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        timeout_ms = max(1000, int(timeout * 1000))
        conn.execute(f"PRAGMA busy_timeout = {timeout_ms};")

        return conn
    except (sqlite3.Error, OSError) as err:
        logger.error("Failed to connect to database at '%s': %s", path_obj, err)
        raise DatabaseConnectionError(
            f"Failed to connect to database at '{path_obj}': {err}"
        ) from err


@contextmanager
def get_connection(
    db_path: Union[Path, str],
    timeout: float = 30.0,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for acquiring and safely closing a database connection.

    Args:
        db_path: Path to the SQLite database file.
        timeout: Lock acquisition timeout in seconds.

    Yields:
        Open sqlite3.Connection.
    """
    conn = create_connection(db_path=db_path, timeout=timeout)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except sqlite3.Error as err:
            logger.warning("Error while closing database connection: %s", err)


@contextmanager
def transaction_scope(
    conn: sqlite3.Connection,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager executing operations within an atomic SQLite transaction.

    Issues an explicit 'BEGIN IMMEDIATE' to prevent race conditions during write
    operations. Commits when exiting cleanly, or rolls back on any exception.

    Args:
        conn: Active sqlite3.Connection.

    Yields:
        The active sqlite3.Connection inside the transaction.

    Raises:
        DatabaseTransactionError: If an error occurs during execution or commit.
    """
    try:
        conn.execute("BEGIN IMMEDIATE;")
        yield conn
        conn.execute("COMMIT;")
    except Exception as exc:
        try:
            conn.execute("ROLLBACK;")
        except sqlite3.Error as rollback_err:
            logger.error("Rollback failed: %s", rollback_err)
        logger.error("Database transaction rolled back due to error: %s", exc)
        if isinstance(exc, DatabaseError):
            raise
        raise DatabaseTransactionError(
            f"Database transaction failed and was rolled back: {exc}"
        ) from exc


@contextmanager
def db_session(
    db_path: Union[Path, str],
    timeout: float = 30.0,
) -> Generator[sqlite3.Connection, None, None]:
    """Convenience context manager combining connection lifecycle and transaction scope.

    Args:
        db_path: Path to the SQLite database.
        timeout: Lock timeout in seconds.

    Yields:
        sqlite3.Connection inside an active, atomic transaction.
    """
    with get_connection(db_path=db_path, timeout=timeout) as conn:
        with transaction_scope(conn) as session:
            yield session
