"""Pydantic schemas for the deterministic anomaly simulation studio."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.api.schemas.ml import DiagnosticReportSchema, PredictionResultSchema


class ScenarioProfileSchema(BaseModel):
    """Metadata describing a deterministic anomaly simulation scenario profile."""

    scenario: str
    name: str
    description: str
    stress_subsystem: str
    expected_risk: str
    is_anomaly_expected: bool


class SimulationRunRequest(BaseModel):
    """Request payload to execute a synthetic anomaly simulation scenario."""

    scenario: str = Field(
        description="Scenario identifier: nominal, cpu_spike, memory_leak, disk_saturation, network_storm, multi_resource_pressure"
    )
    seed: int = Field(default=42, description="Deterministic pseudo-random seed")
    persist: bool = Field(default=False, description="Whether to commit simulated sample into SQLite database")
    overrides: dict[str, Any] = Field(default_factory=dict, description="Optional metric parameter overrides")


class SimulationRunResponse(BaseModel):
    """Consolidated outcome of an end-to-end simulated telemetry run through the ML pipeline."""

    scenario: str
    profile: ScenarioProfileSchema
    persisted: bool
    metric_id: Optional[int] = None
    feature_id: Optional[int] = None
    simulated_metrics: dict[str, Any]
    features_count: int
    prediction: PredictionResultSchema
    diagnostics: DiagnosticReportSchema
