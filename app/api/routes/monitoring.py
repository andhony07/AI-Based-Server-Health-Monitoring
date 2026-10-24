"""Collector daemon and background worker lifecycle REST routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, status

from app.api.dependencies import get_dashboard_service
from app.api.schemas.telemetry import (
    MonitoringControlRequest,
    MonitoringStatusResponse,
)
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/monitoring", tags=["Monitoring Worker"])


@router.get(
    "/status",
    response_model=MonitoringStatusResponse,
    summary="Get background worker status",
    description="Inspects whether the background telemetry collection worker thread is active in the API process.",
)
def get_monitoring_status(
    service: DashboardService = Depends(get_dashboard_service),
) -> MonitoringStatusResponse:
    is_running = service.is_background_monitoring_running()

    # Inspect telemetry freshness
    latest = service.get_latest_metrics()
    freshness_status = "NO_DATA"
    seconds_ago = None
    if latest and latest.timestamp:
        now_utc = datetime.now(timezone.utc)
        ts = latest.timestamp if latest.timestamp.tzinfo is not None else latest.timestamp.replace(tzinfo=timezone.utc)
        seconds_ago = max(0.0, (now_utc - ts).total_seconds())
        if seconds_ago < 60.0:
            freshness_status = "FRESH"
        elif seconds_ago < 300.0:
            freshness_status = "WARM"
        else:
            freshness_status = "STALE"

    message = (
        "Background telemetry collection worker is active."
        if is_running
        else "Background telemetry collection worker is idle."
    )

    return MonitoringStatusResponse(
        is_running=is_running,
        sample_interval=service.settings.metric_collection_interval,
        message=message,
        telemetry_freshness=freshness_status,
        seconds_since_last_sample=round(seconds_ago, 1) if seconds_ago is not None else None,
    )


@router.post(
    "/start",
    response_model=MonitoringStatusResponse,
    summary="Start background collection worker",
    description="Starts a managed background thread collecting and persisting telemetry in SQLite.",
)
def start_monitoring(
    payload: MonitoringControlRequest = Body(default_factory=MonitoringControlRequest),
    service: DashboardService = Depends(get_dashboard_service),
) -> MonitoringStatusResponse:
    if service.is_background_monitoring_running():
        return MonitoringStatusResponse(
            is_running=True,
            sample_interval=service.settings.metric_collection_interval,
            message="Background monitoring worker is already active.",
        )

    requested_interval = payload.interval if payload and payload.interval is not None else None
    started = service.start_background_monitoring(interval=requested_interval)
    if not started:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to start background monitoring worker or already active.",
        )

    interval = requested_interval or service.settings.metric_collection_interval
    return MonitoringStatusResponse(
        is_running=True,
        sample_interval=interval,
        message=f"Started background monitoring worker thread (interval={interval:.1f}s).",
    )


@router.post(
    "/stop",
    response_model=MonitoringStatusResponse,
    summary="Stop background collection worker",
    description="Safely signals and joins the background monitoring thread in this API process.",
)
def stop_monitoring(
    service: DashboardService = Depends(get_dashboard_service),
) -> MonitoringStatusResponse:
    if not service.is_background_monitoring_running():
        return MonitoringStatusResponse(
            is_running=False,
            sample_interval=service.settings.metric_collection_interval,
            message="Background monitoring worker is already idle.",
        )

    stopped = service.stop_background_monitoring(timeout=8.0)
    if not stopped:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Background monitoring worker did not terminate cleanly within timeout.",
        )

    return MonitoringStatusResponse(
        is_running=False,
        sample_interval=service.settings.metric_collection_interval,
        message="Stopped background monitoring worker thread cleanly.",
    )
