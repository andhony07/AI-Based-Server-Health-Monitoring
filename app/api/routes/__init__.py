"""API router registration package."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.anomalies import router as anomalies_router
from app.api.routes.database import router as database_router
from app.api.routes.export import router as export_router
from app.api.routes.features import router as features_router
from app.api.routes.ml import router as ml_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.simulation import router as simulation_router
from app.api.routes.telemetry import router as telemetry_router

api_router = APIRouter()
api_router.include_router(telemetry_router)
api_router.include_router(monitoring_router)
api_router.include_router(ml_router)
api_router.include_router(simulation_router)
api_router.include_router(anomalies_router)
api_router.include_router(features_router)
api_router.include_router(database_router)
api_router.include_router(export_router)

__all__ = ["api_router"]
