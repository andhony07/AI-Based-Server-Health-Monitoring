"""Machine learning predictions, explainable diagnostics, and model status REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_dashboard_service
from app.api.schemas.ml import (
    DiagnosticReportSchema,
    ModelStatusResponse,
    PredictionResultSchema,
)
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/ml", tags=["Machine Learning"])


@router.get(
    "/prediction/latest",
    response_model=PredictionResultSchema,
    summary="Get latest ML prediction and health score",
    description="Evaluates machine learning anomaly detection, deterministic health score, and risk category on latest telemetry.",
)
def get_latest_prediction(
    service: DashboardService = Depends(get_dashboard_service),
) -> PredictionResultSchema:
    prediction = service.get_latest_prediction()
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry feature vector available to evaluate ML predictions. Capture a telemetry snapshot first.",
        )
    return PredictionResultSchema.model_validate(prediction.to_dict())


@router.get(
    "/diagnostics/latest",
    response_model=DiagnosticReportSchema,
    summary="Get explainable diagnostic recommendations report",
    description="Generates an evidence-backed diagnostic report with identified root causes and prioritized remediation actions.",
)
def get_latest_diagnostics(
    service: DashboardService = Depends(get_dashboard_service),
) -> DiagnosticReportSchema:
    report = service.get_diagnostics_for_latest()
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No telemetry available to generate diagnostic report. Capture a telemetry snapshot first.",
        )
    return DiagnosticReportSchema.model_validate(report.to_dict())


@router.get(
    "/model/status",
    response_model=ModelStatusResponse,
    summary="Get active ML model metadata and readiness",
    description="Returns metadata about the active Isolation Forest estimator or fallback heuristic mode.",
)
def get_model_status(
    service: DashboardService = Depends(get_dashboard_service),
) -> ModelStatusResponse:
    is_ready = service.prediction_service.is_model_ready()
    model_name = service.prediction_service.model_name
    metadata = service.prediction_service.metadata

    return ModelStatusResponse(
        is_trained=is_ready,
        model_name=model_name,
        version=metadata.version if metadata else "0.0.0",
        mode="Trained Isolation Forest" if is_ready else "Deterministic Heuristic Baseline",
        expected_features=39,
        training_samples_count=metadata.training_samples_count if metadata else None,
        hyperparameters=metadata.hyperparameters if metadata else {},
        metrics=metadata.metrics if metadata else {},
    )
