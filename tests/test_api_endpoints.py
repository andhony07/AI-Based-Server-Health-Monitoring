"""Comprehensive unit and integration test suite for the FastAPI REST Backend."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.dependencies import get_api_settings, get_dashboard_service
from app.api.main import create_app
from app.core.config import Settings, load_config
from app.dashboard.services.dashboard_service import DashboardService
from app.models.metrics import CPUMetrics, MemoryMetrics, SystemMetrics


@pytest.fixture
def api_test_env(tmp_path: Path) -> Generator[tuple[TestClient, DashboardService, Settings], None, None]:
    """Create an isolated, temporary testing environment for FastAPI REST endpoints."""
    db_file = tmp_path / "test_api.db"
    settings = load_config(
        database_path=db_file,
        data_dir=tmp_path / "data",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
    )
    settings.ensure_directories()

    service = DashboardService(settings=settings)
    app = create_app(settings=settings)

    # Override dependencies for test isolation
    app.dependency_overrides[get_api_settings] = lambda: settings
    app.dependency_overrides[get_dashboard_service] = lambda: service

    with TestClient(app) as client:
        yield client, service, settings

    # Cleanup any active workers and restore overrides
    if service.is_background_monitoring_running():
        service.stop_background_monitoring(timeout=2.0)
    app.dependency_overrides.clear()


class TestRootAndSystemEndpoints:
    """Tests for basic root discovery and health check routes."""

    def test_healthz_endpoint(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, settings = api_test_env
        response = client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["app_name"] == settings.app_name

    def test_root_endpoint(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "version" in data
        assert data["docs_url"] == "/docs"
        assert data["api_prefix"] == "/api"

    def test_cors_headers(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
        response = client.options("/api/telemetry/latest", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


class TestTelemetryEndpoints:
    """Tests for telemetry capture, latest snapshot, and historical metrics."""

    def test_get_latest_telemetry_empty_db(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        response = client.get("/api/telemetry/latest")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metrics"] is None
        assert data["features"] is None
        assert data["prediction"] is None
        assert data["collector_status"] in ("OPERATIONAL", "ERROR")

    def test_capture_snapshot_and_get_latest(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        # Capture snapshot with persistence
        snap_resp = client.post("/api/telemetry/snapshot?persist=true")
        assert snap_resp.status_code == status.HTTP_200_OK
        snap_data = snap_resp.json()
        assert snap_data["success"] is True
        assert snap_data["persisted"] is True
        assert snap_data["metrics"] is not None
        assert "cpu_percent" in snap_data["metrics"]
        assert snap_data["prediction"] is not None
        assert "risk_category" in snap_data["prediction"]

        # Now GET /latest should return populated data
        latest_resp = client.get("/api/telemetry/latest")
        assert latest_resp.status_code == status.HTTP_200_OK
        latest_data = latest_resp.json()
        assert latest_data["metrics"] is not None
        assert latest_data["prediction"] is not None

    def test_get_telemetry_history(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        # Capture 2 snapshots
        client.post("/api/telemetry/snapshot?persist=true")
        client.post("/api/telemetry/snapshot?persist=true")

        hist_resp = client.get("/api/telemetry/history?limit=10")
        assert hist_resp.status_code == status.HTTP_200_OK
        hist_data = hist_resp.json()
        assert hist_data["count"] == 2
        assert len(hist_data["records"]) == 2

    def test_telemetry_history_validation_error(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        # Negative limit triggers Pydantic/FastAPI validation error
        resp = client.get("/api/telemetry/history?limit=-5")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestMonitoringWorkerEndpoints:
    """Tests for background collection worker lifecycle."""

    def test_monitoring_status_idle(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/monitoring/status")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["is_running"] is False
        assert "idle" in data["message"].lower()

    def test_start_and_stop_monitoring(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, service, _ = api_test_env
        if service.is_background_monitoring_running():
            service.stop_background_monitoring(timeout=8.0)

        # Start worker
        start_resp = client.post("/api/monitoring/start", json={"interval": 1.0})
        assert start_resp.status_code == status.HTTP_200_OK
        start_data = start_resp.json()
        assert start_data["is_running"] is True
        assert service.is_background_monitoring_running() is True

        # Idempotent second start
        start_again = client.post("/api/monitoring/start", json={"interval": 1.0})
        assert start_again.status_code == status.HTTP_200_OK
        assert "already" in start_again.json()["message"].lower()

        # Stop worker
        stop_resp = client.post("/api/monitoring/stop")
        assert stop_resp.status_code == status.HTTP_200_OK
        assert stop_resp.json()["is_running"] is False
        assert service.is_background_monitoring_running() is False

    def test_monitoring_start_invalid_interval(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, service, _ = api_test_env
        if service.is_background_monitoring_running():
            service.stop_background_monitoring(timeout=8.0)

        resp = client.post("/api/monitoring/start", json={"interval": 0.1})
        assert resp.status_code in (status.HTTP_422_UNPROCESSABLE_ENTITY, 422)


class TestMLEndpoints:
    """Tests for ML predictions, explainable diagnostics, and model status."""

    def test_ml_prediction_404_when_empty(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/ml/prediction/latest")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ml_diagnostics_404_when_empty(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/ml/diagnostics/latest")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ml_prediction_and_diagnostics_after_snapshot(
        self, api_test_env: tuple[TestClient, DashboardService, Settings]
    ) -> None:
        client, _, _ = api_test_env
        client.post("/api/telemetry/snapshot?persist=true")

        # Test prediction
        pred_resp = client.get("/api/ml/prediction/latest")
        assert pred_resp.status_code == status.HTTP_200_OK
        pred_data = pred_resp.json()
        assert "risk_category" in pred_data
        assert "anomaly_score" in pred_data
        assert "health_score" in pred_data

        # Test diagnostics
        diag_resp = client.get("/api/ml/diagnostics/latest")
        assert diag_resp.status_code == status.HTTP_200_OK
        diag_data = diag_resp.json()
        assert "recommendations" in diag_data
        assert "summary_headline" in diag_data

    def test_ml_model_status(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/ml/model/status")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert "is_trained" in data
        assert "model_name" in data
        assert data["expected_features"] == 39


class TestSimulationEndpoints:
    """Tests for the deterministic anomaly simulation studio."""

    def test_list_scenarios(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/simulation/scenarios")
        assert resp.status_code == status.HTTP_200_OK
        scenarios = resp.json()
        assert len(scenarios) == 6
        scenario_keys = {s["scenario"] for s in scenarios}
        assert "nominal" in scenario_keys
        assert "cpu_spike" in scenario_keys
        assert "memory_leak" in scenario_keys
        assert "disk_saturation" in scenario_keys
        assert "network_storm" in scenario_keys
        assert "multi_resource_pressure" in scenario_keys

    def test_run_simulation_nominal(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        payload = {"scenario": "nominal", "seed": 42, "persist": False}
        resp = client.post("/api/simulation/run", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["scenario"] == "nominal"
        assert data["profile"]["stress_subsystem"] == "None (Healthy)"
        assert data["persisted"] is False
        assert data["prediction"]["risk_category"] in ("Normal", "Low", "Moderate")
        assert data["features_count"] == 39
        assert len(data["diagnostics"]["recommendations"]) >= 0

    def test_run_simulation_cpu_spike(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        payload = {"scenario": "cpu_spike", "seed": 42, "persist": True}
        resp = client.post("/api/simulation/run", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["scenario"] == "cpu_spike"
        assert data["persisted"] is True
        assert data["prediction"]["is_anomaly"] is True
        assert data["prediction"]["risk_category"] in ("Critical", "High")
        assert data["diagnostics"]["critical_count"] > 0

    def test_run_simulation_invalid_scenario(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        payload = {"scenario": "non_existent_chaos_mode"}
        resp = client.post("/api/simulation/run", json=payload)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid scenario" in resp.json()["detail"]


class TestAnomalyAndFeatureHistoryEndpoints:
    """Tests for anomaly audit log and 39-feature vector history."""

    def test_get_anomalies_history(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        # Generate samples
        client.post("/api/simulation/run", json={"scenario": "nominal", "persist": True})
        client.post("/api/simulation/run", json={"scenario": "cpu_spike", "persist": True})

        resp = client.get("/api/anomalies/history?limit=10")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["count"] == 2

        # Filter strictly anomalies
        anom_resp = client.get("/api/anomalies/history?limit=10&anomalies_only=true")
        assert anom_resp.status_code == status.HTTP_200_OK
        anom_data = anom_resp.json()
        for item in anom_data["anomalies"]:
            assert item["is_anomaly"] is True

    def test_get_features_history(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        client.post("/api/simulation/run", json={"scenario": "nominal", "persist": True})

        resp = client.get("/api/features/history?limit=5")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data) >= 1
        assert "cpu_utilization_percent" in data[0]["features"]


class TestDatabaseAndSystemStatusEndpoints:
    """Tests for operational status, database summary, and validation logs."""

    def test_system_status(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/system/status")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["overall_status"] in ("HEALTHY", "DEGRADED", "CRITICAL")
        assert "subsystems" in data
        assert "database" in data["subsystems"]
        assert "ml_engine" in data["subsystems"]
        assert "collector" in data["subsystems"]

    def test_database_summary(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        resp = client.get("/api/database/summary")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["database_exists"] is True
        assert "counts" in data
        assert "system_metrics" in data["counts"]

    def test_database_validation_logs(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        client.post("/api/telemetry/snapshot?persist=true")
        resp = client.get("/api/database/validation-logs?limit=5")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "is_valid" in data[0]


class TestExportEndpoints:
    """Tests for RFC-4180 compliant CSV stream generation."""

    def test_export_metrics_csv(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        client.post("/api/telemetry/snapshot?persist=true")

        resp = client.get("/api/export/metrics.csv")
        assert resp.status_code == status.HTTP_200_OK
        assert "text/csv" in resp.headers["content-type"]
        assert "attachment" in resp.headers.get("content-disposition", "")
        lines = resp.text.strip().splitlines()
        assert len(lines) >= 2  # Header + at least 1 record
        assert "cpu_percent" in lines[0]
        assert "memory_percent" in lines[0]

    def test_export_anomalies_csv(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        client.post("/api/simulation/run", json={"scenario": "cpu_spike", "persist": True})

        resp = client.get("/api/export/anomalies.csv")
        assert resp.status_code == status.HTTP_200_OK
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().splitlines()
        assert len(lines) >= 2
        assert "anomaly_score" in lines[0]
        assert "is_anomaly" in lines[0]

    def test_export_features_csv(self, api_test_env: tuple[TestClient, DashboardService, Settings]) -> None:
        client, _, _ = api_test_env
        client.post("/api/simulation/run", json={"scenario": "nominal", "persist": True})

        resp = client.get("/api/export/features.csv")
        assert resp.status_code == status.HTTP_200_OK
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().splitlines()
        assert len(lines) >= 2
        assert "feature_id" in lines[0]
        assert "cpu_utilization_percent" in lines[0]
