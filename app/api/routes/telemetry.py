"""Telemetry and hardware metrics REST routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_dashboard_service
from app.api.schemas.telemetry import (
    HistoricalTelemetryResponse,
    LatestTelemetryResponse,
    SnapshotResponse,
    SystemMetricRecordSchema,
)
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get(
    "/latest",
    response_model=LatestTelemetryResponse,
    summary="Get latest system telemetry snapshot",
    description="Fetches the most recent hardware metric sample, engineered feature vector, and ML health prediction.",
)
def get_latest_telemetry(
    service: DashboardService = Depends(get_dashboard_service),
) -> LatestTelemetryResponse:
    latest_metric = service.get_latest_metrics()
    latest_feat = service.get_latest_feature_vector()
    latest_pred = service.get_latest_prediction()

    # Determine collector status safely
    collector_status = "OPERATIONAL"
    try:
        import psutil

        psutil.cpu_percent(interval=0.0)
    except Exception:
        collector_status = "ERROR"

    return LatestTelemetryResponse(
        metrics=SystemMetricRecordSchema.model_validate(latest_metric) if latest_metric else None,
        features=latest_feat if latest_feat else None,
        prediction=latest_pred.to_dict() if latest_pred else None,
        collector_status=collector_status,
        timestamp=latest_metric.timestamp if latest_metric else datetime.now(timezone.utc),
    )


@router.post(
    "/snapshot",
    response_model=SnapshotResponse,
    summary="Capture live on-demand telemetry snapshot",
    description="Captures live hardware readings from psutil, preprocessed features, persists to SQLite, and evaluates ML risk.",
)
def capture_snapshot(
    persist: bool = Query(default=True, description="Whether to atomically persist sample into SQLite"),
    service: DashboardService = Depends(get_dashboard_service),
) -> SnapshotResponse:
    metric_record, prediction, err = service.capture_live_snapshot(persist=persist)
    if err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to capture live telemetry snapshot: {err}",
        )

    return SnapshotResponse(
        success=True,
        persisted=persist,
        metrics=SystemMetricRecordSchema.model_validate(metric_record) if metric_record else None,
        prediction=prediction.to_dict() if prediction else None,
        error=None,
    )


@router.get(
    "/history",
    response_model=HistoricalTelemetryResponse,
    summary="Get historical hardware metrics",
    description="Queries historical hardware telemetry records ordered chronologically.",
)
def get_telemetry_history(
    limit: int = Query(default=500, ge=1, le=5000, description="Maximum number of historical records"),
    start_time: Optional[datetime] = Query(default=None, description="Optional ISO start timestamp filter"),
    end_time: Optional[datetime] = Query(default=None, description="Optional ISO end timestamp filter"),
    service: DashboardService = Depends(get_dashboard_service),
) -> HistoricalTelemetryResponse:
    records = service.get_historical_metrics(
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    validated_records = [SystemMetricRecordSchema.model_validate(r) for r in records]
    return HistoricalTelemetryResponse(
        count=len(validated_records),
        limit=limit,
        records=validated_records,
    )
