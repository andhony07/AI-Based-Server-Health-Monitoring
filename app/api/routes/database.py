"""Database inspection and operational system status REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_dashboard_service
from app.api.schemas.database import (
    DatabaseSummaryResponse,
    OperationalStatusResponse,
    ValidationLogRecordSchema,
)
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(tags=["Database & System Status"])


@router.get(
    "/system/status",
    response_model=OperationalStatusResponse,
    summary="Get platform operational health status",
    description="Performs non-destructive health checks across SQLite integrity, ML engine status, psutil collector health, and telemetry freshness.",
)
def get_system_status(
    service: DashboardService = Depends(get_dashboard_service),
) -> OperationalStatusResponse:
    status_data = service.get_operational_status()
    return OperationalStatusResponse.model_validate(status_data)


@router.get(
    "/database/summary",
    response_model=DatabaseSummaryResponse,
    summary="Get SQLite database state summary",
    description="Inspects SQLite database file size, path, table counts, and chronological boundaries.",
)
def get_database_summary(
    service: DashboardService = Depends(get_dashboard_service),
) -> DatabaseSummaryResponse:
    summary_data = service.get_database_summary()
    return DatabaseSummaryResponse.model_validate(summary_data)


@router.get(
    "/database/validation-logs",
    response_model=list[ValidationLogRecordSchema],
    summary="Get recent preprocessing validation logs",
    description="Fetches recent audit log entries from the validation_logs table.",
)
def get_validation_logs(
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of validation log rows"),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[ValidationLogRecordSchema]:
    records = service.get_recent_validation_logs(limit=limit)
    return [ValidationLogRecordSchema.model_validate(r) for r in records]
