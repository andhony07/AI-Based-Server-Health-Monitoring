"""Deterministic anomaly simulation REST routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_dashboard_service
from app.api.schemas.ml import DiagnosticReportSchema, PredictionResultSchema
from app.api.schemas.simulation import (
    ScenarioProfileSchema,
    SimulationRunRequest,
    SimulationRunResponse,
)
from app.dashboard.services.dashboard_service import DashboardService
from app.ml.simulation import SCENARIO_PROFILES, SimulationScenario

router = APIRouter(prefix="/simulation", tags=["Anomaly Simulation"])


@router.get(
    "/scenarios",
    response_model=list[ScenarioProfileSchema],
    summary="List all available deterministic anomaly simulation scenarios",
    description="Returns metadata profiles for all supported failure simulation scenarios.",
)
def list_scenarios() -> list[ScenarioProfileSchema]:
    profiles = []
    for sc_enum, profile in SCENARIO_PROFILES.items():
        profiles.append(
            ScenarioProfileSchema(
                scenario=sc_enum.value,
                name=profile.name,
                description=profile.description,
                stress_subsystem=profile.stress_subsystem,
                expected_risk=profile.expected_risk.value,
                is_anomaly_expected=profile.is_anomaly_expected,
            )
        )
    return profiles


@router.post(
    "/run",
    response_model=SimulationRunResponse,
    summary="Execute a deterministic anomaly simulation",
    description="Runs synthetic telemetry through the full feature engineering and ML prediction pipeline without stressing host OS hardware.",
)
def run_simulation(
    payload: SimulationRunRequest,
    service: DashboardService = Depends(get_dashboard_service),
) -> SimulationRunResponse:
    # Validate scenario
    valid_scenarios = [s.value for s in SimulationScenario]
    if payload.scenario not in valid_scenarios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid scenario '{payload.scenario}'. Must be one of: "
                f"{', '.join(valid_scenarios)}"
            ),
        )

    try:
        scenario_enum = SimulationScenario(payload.scenario)
        sim_res, diag_report = service.run_simulation(
            scenario=scenario_enum,
            persist=payload.persist,
            seed=payload.seed,
            **payload.overrides,
        )

        profile = SCENARIO_PROFILES[scenario_enum]

        # Convert simulated metrics to dictionary for response
        metrics_dict: dict[str, Any] = {
            "timestamp": sim_res.metrics.timestamp.isoformat(),
            "cpu": {
                "utilization_percent": sim_res.metrics.cpu.utilization_percent if sim_res.metrics.cpu else 0.0,
                "logical_cores": sim_res.metrics.cpu.logical_cores if sim_res.metrics.cpu else 1,
            },
            "memory": {
                "utilization_percent": sim_res.metrics.memory.utilization_percent if sim_res.metrics.memory else 0.0,
                "used_mb": sim_res.metrics.memory.used_mb if sim_res.metrics.memory else 0.0,
                "total_mb": sim_res.metrics.memory.total_mb if sim_res.metrics.memory else 0.0,
            },
            "disk": {
                "utilization_percent": sim_res.metrics.disk.utilization_percent if sim_res.metrics.disk else 0.0,
                "used_gb": round(sim_res.metrics.disk.used_bytes / (1024**3), 2) if sim_res.metrics.disk else 0.0,
                "total_gb": round(sim_res.metrics.disk.total_bytes / (1024**3), 2) if sim_res.metrics.disk else 0.0,
            },
            "network": {
                "upload_kbps": sim_res.metrics.network.upload_kbps if sim_res.metrics.network else 0.0,
                "download_kbps": sim_res.metrics.network.download_kbps if sim_res.metrics.network else 0.0,
            },
            "process_count": len(sim_res.metrics.processes),
        }

        return SimulationRunResponse(
            scenario=payload.scenario,
            profile=ScenarioProfileSchema(
                scenario=scenario_enum.value,
                name=profile.name,
                description=profile.description,
                stress_subsystem=profile.stress_subsystem,
                expected_risk=profile.expected_risk.value,
                is_anomaly_expected=profile.is_anomaly_expected,
            ),
            persisted=sim_res.persisted,
            metric_id=sim_res.metric_id,
            feature_id=sim_res.feature_id,
            simulated_metrics=metrics_dict,
            features_count=len(sim_res.processed.feature_vector.features),
            prediction=PredictionResultSchema.model_validate(sim_res.prediction.to_dict()),
            diagnostics=DiagnosticReportSchema.model_validate(diag_report.to_dict()),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation execution failed: {exc}",
        ) from exc
