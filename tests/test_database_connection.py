"""Unit tests for SQLite connection lifecycle, transaction scopes, and error handling."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.database.connection import (
    DatabaseConnectionError,
    DatabaseTransactionError,
    create_connection,
    db_session,
    get_connection,
    transaction_scope,
)


class TestDatabaseConnection:
    """Test suite for database connection creation and configuration."""

    def test_create_connection_configures_pragmas(self, tmp_path: Path) -> None:
        """Verify that newly created connections have WAL, foreign keys, and Row factory configured."""
        db_path = tmp_path / "test.db"
        conn = create_connection(db_path, timeout=5.0)

        try:
            # Check row factory
            assert conn.row_factory == sqlite3.Row

            # Check foreign keys
            fk_cursor = conn.execute("PRAGMA foreign_keys;")
            assert fk_cursor.fetchone()[0] == 1

            # Check journal mode (WAL or memory if in-memory)
            jm_cursor = conn.execute("PRAGMA journal_mode;")
            journal_mode = jm_cursor.fetchone()[0].upper()
            assert journal_mode in ("WAL", "DELETE", "MEMORY")

            # Check busy timeout
            to_cursor = conn.execute("PRAGMA busy_timeout;")
            assert to_cursor.fetchone()[0] >= 1000
        finally:
            conn.close()

    def test_create_connection_creates_parent_directories(self, tmp_path: Path) -> None:
        """Verify that create_connection creates parent directories if they don't exist."""
        nested_dir = tmp_path / "deeply" / "nested" / "subfolder"
        db_path = nested_dir / "telemetry.db"
        assert not nested_dir.exists()

        conn = create_connection(db_path)
        try:
            assert nested_dir.is_dir()
            assert db_path.exists()
        finally:
            conn.close()

    def test_get_connection_context_manager_closes_cleanly(self, tmp_path: Path) -> None:
        """Verify get_connection yields an active connection and closes it upon exit."""
        db_path = tmp_path / "ctx_test.db"
        saved_conn = None

        with get_connection(db_path) as conn:
            saved_conn = conn
            cursor = conn.execute("SELECT 1 AS num;")
            assert cursor.fetchone()["num"] == 1

        # Connection should now be closed
        assert saved_conn is not None
        with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed database"):
            saved_conn.execute("SELECT 1;")

    def test_transaction_scope_commits_on_success(self, tmp_path: Path) -> None:
        """Verify transaction_scope commits modifications when no exceptions are raised."""
        db_path = tmp_path / "tx_commit.db"

        with get_connection(db_path) as conn:
            conn.execute("CREATE TABLE test_tx (id INTEGER PRIMARY KEY, val TEXT);")
            with transaction_scope(conn):
                conn.execute("INSERT INTO test_tx (val) VALUES ('persisted');")

            # Check from same connection outside transaction block
            row = conn.execute("SELECT val FROM test_tx WHERE id = 1;").fetchone()
            assert row["val"] == "persisted"

        # Check from a new connection to confirm it persisted on disk
        with get_connection(db_path) as new_conn:
            row = new_conn.execute("SELECT val FROM test_tx WHERE id = 1;").fetchone()
            assert row["val"] == "persisted"

    def test_transaction_scope_rolls_back_on_exception(self, tmp_path: Path) -> None:
        """Verify transaction_scope rolls back all changes if an exception occurs."""
        db_path = tmp_path / "tx_rollback.db"

        with get_connection(db_path) as conn:
            conn.execute("CREATE TABLE test_rollback (id INTEGER PRIMARY KEY, val TEXT);")
            conn.execute("INSERT INTO test_rollback (val) VALUES ('initial');")

            with pytest.raises(DatabaseTransactionError):
                with transaction_scope(conn):
                    conn.execute("INSERT INTO test_rollback (val) VALUES ('temporary');")
                    raise RuntimeError("Simulated mid-transaction failure")

            # The temporary insert should have been rolled back
            rows = conn.execute("SELECT val FROM test_rollback;").fetchall()
            assert len(rows) == 1
            assert rows[0]["val"] == "initial"

    def test_db_session_convenience_manager(self, tmp_path: Path) -> None:
        """Verify db_session combines connection lifecycle and transaction commit."""
        db_path = tmp_path / "session_test.db"

        with db_session(db_path) as session:
            session.execute("CREATE TABLE session_tbl (key TEXT, val INTEGER);")
            session.execute("INSERT INTO session_tbl VALUES ('cpu', 42);")

        with get_connection(db_path) as conn:
            row = conn.execute("SELECT val FROM session_tbl WHERE key = 'cpu';").fetchone()
            assert row["val"] == 42
