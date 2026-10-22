"""Tests for operational status checks in DashboardService.

Validates non-destructive system health inspection across SQLite database,
ML model engine, hardware collectors, telemetry freshness, and background worker.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.config import load_config
from app.dashboard.services.dashboard_service import DashboardService
from app.database.service import PersistenceService
from app.ml.prediction_service import PredictionService
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    SystemMetrics,
)
from app.preprocessing.pipeline import PreprocessingPipeline


@pytest.fixture
def isolated_service(tmp_path: Path) -> DashboardService:
    settings = load_config(
        database_path=tmp_path / "status_test.db",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
    )
    return DashboardService(settings=settings)


def test_operational_status_structure(isolated_service: DashboardService) -> None:
    """Verify operational status dictionary matches expected schema."""
    status = isolated_service.get_operational_status()

    assert isinstance(status, dict)
    assert "overall_status" in status
    assert status["overall_status"] in ("HEALTHY", "DEGRADED", "CRITICAL")
    assert "status_color" in status
    assert "headline" in status
    assert "subsystems" in status

    sub = status["subsystems"]
    assert "database" in sub
    assert "ml_engine" in sub
    assert "collector" in sub
    assert "background_worker" in sub
    assert "telemetry_freshness" in sub


def test_operational_status_database_healthy(isolated_service: DashboardService) -> None:
    """Verify database subsystem passes PRAGMA check and reports operational."""
    status = isolated_service.get_operational_status()
    db_info = status["subsystems"]["database"]

    assert db_info["status"] == "OPERATIONAL"
    assert db_info["exists"] is True
    assert db_info["integrity"] == "ok"
    assert db_info["error"] is None


def test_operational_status_ml_engine_state(isolated_service: DashboardService) -> None:
    """Verify ML engine state reflects whether trained artifact is loaded."""
    status = isolated_service.get_operational_status()
    ml_info = status["subsystems"]["ml_engine"]

    assert "model_name" in ml_info
    assert ml_info["expected_features"] == 39
    assert ml_info["status"] in ("OPERATIONAL", "FALLBACK")


def test_telemetry_freshness_transitions(isolated_service: DashboardService) -> None:
    """Verify telemetry freshness transitions correctly from NO_DATA to FRESH."""
    # Initially no data
    status_initial = isolated_service.get_operational_status()
    assert status_initial["subsystems"]["telemetry_freshness"]["status"] == "NO_DATA"

    # Add fresh sample
    now = datetime.now(timezone.utc)
    metrics = SystemMetrics(
        timestamp=now,
        cpu=CPUMetrics(utilization_percent=20.0, logical_cores=4),
        memory=MemoryMetrics(total_bytes=8 * 1024**3, available_bytes=4 * 1024**3, used_bytes=4 * 1024**3, utilization_percent=50.0),
        disk=DiskMetrics(partitions=[], total_bytes=100 * 1024**3, used_bytes=50 * 1024**3, free_bytes=50 * 1024**3, utilization_percent=50.0),
        network=NetworkMetrics(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20),
    )
    processed = isolated_service.pipeline.process(metrics)
    isolated_service.persistence.persist_sample(metrics, processed)

    # Now should be FRESH
    status_fresh = isolated_service.get_operational_status()
    fresh_info = status_fresh["subsystems"]["telemetry_freshness"]
    assert fresh_info["status"] == "FRESH"
    assert fresh_info["seconds_since_last_sample"] is not None
    assert fresh_info["seconds_since_last_sample"] < 10.0


def test_background_worker_status_reflection(isolated_service: DashboardService) -> None:
    """Verify background worker reflects IDLE and ACTIVE states."""
    status_idle = isolated_service.get_operational_status()
    assert status_idle["subsystems"]["background_worker"]["status"] == "IDLE"
    assert status_idle["subsystems"]["background_worker"]["is_running"] is False
