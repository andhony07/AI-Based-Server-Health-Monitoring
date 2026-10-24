"""FastAPI REST API package for AI-Based Server Health Monitoring.

Exposes REST endpoints for telemetry, ML health inference, explainable diagnostics,
simulation, anomaly audit logs, database inspection, and CSV telemetry exports.
"""

from __future__ import annotations

from app.api.main import create_app

__all__ = ["create_app"]
