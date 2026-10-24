"""Feature vector historical inspection REST routes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_dashboard_service
from app.api.schemas.telemetry import FeatureVectorRecordSchema
from app.dashboard.services.dashboard_service import DashboardService

router = APIRouter(prefix="/features", tags=["Features"])


@router.get(
    "/history",
    response_model=list[FeatureVectorRecordSchema],
    summary="Get historical 39-feature vectors",
    description="Fetches engineered 39-feature vectors ordered chronologically.",
)
def get_features_history(
    limit: int = Query(default=500, ge=1, le=5000, description="Maximum number of historical records"),
    start_time: Optional[datetime] = Query(default=None, description="Optional start timestamp filter (UTC)"),
    end_time: Optional[datetime] = Query(default=None, description="Optional end timestamp filter (UTC)"),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[FeatureVectorRecordSchema]:
    records = service.get_historical_features(
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    return [FeatureVectorRecordSchema.model_validate(r) for r in records]
