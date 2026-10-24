"""RFC-4180 compliant CSV telemetry and anomaly data export routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import get_dashboard_service
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/export", tags=["Data Export"])


@router.get(
    "/metrics.csv",
    summary="Export telemetry metrics as CSV",
    description="Generates an RFC-4180 compliant CSV stream containing historical system metrics.",
    response_class=Response,
)
def export_metrics_csv(
    limit: int = Query(default=500, ge=1, le=10000, description="Maximum rows to export"),
    start_time: Optional[datetime] = Query(default=None, description="Optional start timestamp filter (UTC)"),
    end_time: Optional[datetime] = Query(default=None, description="Optional end timestamp filter (UTC)"),
    service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    csv_content = service.export_metrics_csv(start_time=start_time, end_time=end_time, limit=limit)
    filename = f"system_metrics_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/anomalies.csv",
    summary="Export evaluated anomaly audit log as CSV",
    description="Generates an RFC-4180 compliant CSV stream containing historical evaluated anomalies and risk levels.",
    response_class=Response,
)
def export_anomalies_csv(
    limit: int = Query(default=500, ge=1, le=10000, description="Maximum rows to export"),
    anomalies_only: bool = Query(default=False, description="Filter strictly to samples where is_anomaly is True"),
    service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    csv_content = service.export_anomalies_csv(limit=limit, filter_anomalies_only=anomalies_only)
    filename = f"anomalies_audit_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/features.csv",
    summary="Export 39-feature vectors as CSV",
    description="Generates an RFC-4180 compliant CSV stream containing historical engineered 39-feature vectors.",
    response_class=Response,
)
def export_features_csv(
    limit: int = Query(default=500, ge=1, le=10000, description="Maximum rows to export"),
    start_time: Optional[datetime] = Query(default=None, description="Optional start timestamp filter (UTC)"),
    end_time: Optional[datetime] = Query(default=None, description="Optional end timestamp filter (UTC)"),
    service: DashboardService = Depends(get_dashboard_service),
) -> Response:
    csv_content = service.export_features_csv(start_time=start_time, end_time=end_time, limit=limit)
    filename = f"features_export_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
