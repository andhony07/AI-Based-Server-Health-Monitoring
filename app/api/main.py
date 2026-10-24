"""FastAPI application factory and server entry point.

Configures CORS, lifespan shutdown management, structured logging,
and REST routing for the AI-Based Server Health Monitoring platform.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies import get_api_settings, get_dashboard_service
from app.api.routes import api_router
from app.core.config import Settings
from app.core.logging_config import get_logger

logger = get_logger("app.api")


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup initialization and graceful shutdown."""
    settings = get_api_settings()
    logger.info("Initializing %s API backend (v%s)...", settings.app_name, settings.app_version)
    logger.info("Configured CORS Allowed Origins: %s", settings.cors_origins)

    yield

    # Clean shutdown: Terminate background monitoring worker if running in this API process
    try:
        service = get_dashboard_service()
        if service.is_background_monitoring_running():
            logger.info("Terminating API background monitoring worker...")
            service.stop_background_monitoring(timeout=3.0)
            logger.info("API background monitoring worker terminated.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Error during API shutdown cleanup: %s", exc)


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Create and configure a FastAPI application instance.

    Args:
        settings: Optional custom Settings instance.

    Returns:
        Configured FastAPI application ready for serving via Uvicorn.
    """
    active_settings = settings or get_api_settings()

    app = FastAPI(
        title=f"{active_settings.app_name} API",
        version=active_settings.app_version,
        description=(
            "Unified REST API backend connecting modern web frontends (e.g. React/TypeScript) "
            "to hardware telemetry collectors, preprocessing pipeline, SQLite persistence, "
            "and ML predictive health/anomaly models."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=app_lifespan,
    )

    # Configure Cross-Origin Resource Sharing (CORS) for React dev servers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled server exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "detail": f"Internal server error: {exc}",
                "path": request.url.path,
            },
        )

    # Health check & Root discovery endpoints
    @app.get(
        "/healthz",
        tags=["System Status"],
        summary="Basic API liveness probe",
    )
    def health_check() -> dict[str, str]:
        return {"status": "ok", "app_name": active_settings.app_name}

    @app.get(
        "/",
        tags=["System Status"],
        summary="API root info",
    )
    def root_info() -> dict[str, str]:
        return {
            "app_name": active_settings.app_name,
            "version": active_settings.app_version,
            "docs_url": "/docs",
            "api_prefix": "/api",
        }

    # Mount all audited API routers under /api prefix
    app.include_router(api_router, prefix="/api")

    return app


# Default application instance for Uvicorn ASGI runner
app = create_app()
