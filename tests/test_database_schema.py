"""Unit tests for schema creation, versioning, migrations, and foreign key integrity."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.database.connection import get_connection
from app.database.migrations import apply_migrations, get_current_schema_version
from app.database.schema import FEATURE_COLUMNS, SCHEMA_VERSION


class TestDatabaseSchema:
    """Test suite for schema tables, versioning, and constraint validation."""

    def test_schema_migrations_initializes_empty_database(self, tmp_path: Path) -> None:
        """Verify initial empty database starts at version 0 and upgrades to current SCHEMA_VERSION."""
        db_path = tmp_path / "schema_test.db"

        with get_connection(db_path) as conn:
            assert get_current_schema_version(conn) == 0

            version = apply_migrations(conn)
            assert version == SCHEMA_VERSION
            assert get_current_schema_version(conn) == SCHEMA_VERSION

    def test_all_expected_tables_created(self, tmp_path: Path) -> None:
        """Verify schema migrations create all expected relational tables and indexes."""
        db_path = tmp_path / "tables_test.db"

        with get_connection(db_path) as conn:
            apply_migrations(conn)

            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row["name"] for row in cursor.fetchall()}

            expected_tables = {
                "schema_migrations",
                "system_metrics",
                "feature_vectors",
                "validation_logs",
            }
            assert expected_tables.issubset(tables)

    def test_feature_vectors_table_contains_all_39_features(self, tmp_path: Path) -> None:
        """Verify the feature_vectors table schema has distinct columns for all 39 features."""
        db_path = tmp_path / "features_schema.db"

        with get_connection(db_path) as conn:
            apply_migrations(conn)

            cursor = conn.execute("PRAGMA table_info(feature_vectors);")
            column_names = {row["name"] for row in cursor.fetchall()}

            assert len(FEATURE_COLUMNS) == 39
            for col in FEATURE_COLUMNS:
                assert col in column_names, f"Feature column '{col}' missing from schema."

            assert "metric_id" in column_names
            assert "timestamp" in column_names
            assert "features_json" in column_names
            assert "metadata_json" in column_names

    def test_foreign_key_enforcement(self, tmp_path: Path) -> None:
        """Verify foreign key constraint rejects referencing a non-existent system_metrics id."""
        db_path = tmp_path / "fk_test.db"

        with get_connection(db_path) as conn:
            apply_migrations(conn)

            # Inserting feature_vectors row with non-existent metric_id 99999 should fail
            feature_cols = ", ".join(FEATURE_COLUMNS)
            placeholders = ", ".join(["0.0"] * len(FEATURE_COLUMNS))
            sql = f"""
            INSERT INTO feature_vectors (metric_id, timestamp, {feature_cols}, features_json, metadata_json)
            VALUES (99999, '2026-10-01T12:00:00+00:00', {placeholders}, '{{}}', '{{}}');
            """
            with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
                conn.execute(sql)

    def test_schema_initialization_is_idempotent(self, tmp_path: Path) -> None:
        """Verify repeatedly running migrations does not alter existing data or fail."""
        db_path = tmp_path / "idempotent.db"

        with get_connection(db_path) as conn:
            apply_migrations(conn)

            # Insert sample data
            conn.execute(
                """
                INSERT INTO system_metrics (timestamp, raw_payload_json)
                VALUES ('2026-10-01T12:00:00+00:00', '{"test": 1}');
                """
            )

            # Apply migrations again
            version = apply_migrations(conn)
            assert version == SCHEMA_VERSION

            # Confirm previously inserted data is preserved
            row = conn.execute("SELECT COUNT(*) AS total FROM system_metrics;").fetchone()
            assert row["total"] == 1
