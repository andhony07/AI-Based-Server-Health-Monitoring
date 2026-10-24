"""Anomaly history and audit log REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_dashboard_service
from app.api.schemas.ml import (
    AnomalyAuditItemSchema,
    HistoricalAnomaliesResponse,
)
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/anomalies", tags=["Anomaly Audit"])


@router.get(
    "/history",
    response_model=HistoricalAnomaliesResponse,
    summary="Get historical evaluated anomaly audit log",
    description="Queries and scores recent historical feature vectors, returning anomaly probabilities, risk categories, and correlated telemetry.",
)
def get_anomalies_history(
    limit: int = Query(default=200, ge=1, le=1000, description="Maximum number of historical records to evaluate"),
    anomalies_only: bool = Query(default=False, description="Filter strictly to samples flagged as anomalous"),
    service: DashboardService = Depends(get_dashboard_service),
) -> HistoricalAnomaliesResponse:
    results = service.get_historical_anomalies(limit=limit)

    if anomalies_only:
        results = [a for a in results if a.get("is_anomaly", False)]

    items = [
        AnomalyAuditItemSchema(
            feature_id=r["feature_id"],
            metric_id=r.get("metric_id"),
            timestamp=r["timestamp"],
            anomaly_score=r["anomaly_score"],
            is_anomaly=r["is_anomaly"],
            health_score=r.get("health_score"),
            risk_category=r["risk_category"],
            model_name=r["model_name"],
            is_trained_model=r["is_trained_model"],
            cpu_percent=r.get("cpu_percent"),
            memory_percent=r.get("memory_percent"),
            disk_percent=r.get("disk_percent"),
            network_kbps=r.get("network_kbps"),
        )
        for r in results
    ]

    return HistoricalAnomaliesResponse(
        count=len(items),
        limit=limit,
        anomalies=items,
    )
