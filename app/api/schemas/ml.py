"""Pydantic schemas for machine learning predictions, health scoring, and diagnostics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnomalyResultSchema(BaseModel):
    """Anomaly detection evaluation outcome schema."""

    is_anomaly: bool
    raw_score: float
    normalized_score: float = Field(ge=0.0, le=1.0)
    threshold: float = 0.0


class HealthScoreResultSchema(BaseModel):
    """Health score calculation outcome schema."""

    score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    status: str
    contributing_factors: dict[str, float] = Field(default_factory=dict)
    explanation: str = ""


class PredictionResultSchema(BaseModel):
    """Consolidated ML prediction report schema."""

    timestamp: datetime
    is_anomaly: bool
    anomaly_score: float = Field(ge=0.0, le=1.0)
    raw_decision_score: float
    health_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    risk_category: str
    model_name: str
    model_version: str
    warnings: list[str] = Field(default_factory=list)


class DiagnosticEvidenceSchema(BaseModel):
    """Empirical telemetry evidence item supporting a diagnostic recommendation."""

    metric_name: str
    observed_value: Any
    threshold: str
    level: str
    description: str


class DiagnosticRecommendationSchema(BaseModel):
    """Actionable operational recommendation backed by telemetry evidence."""

    id: str
    category: str
    severity: str
    title: str
    summary: str
    root_cause_hypothesis: str
    evidence: list[DiagnosticEvidenceSchema] = Field(default_factory=list)
    remediation_steps: list[str] = Field(default_factory=list)
    target_component: Optional[str] = None


class DiagnosticReportSchema(BaseModel):
    """Consolidated explainable diagnostic report schema."""

    timestamp: str
    overall_health_score: Optional[float] = None
    risk_category: str
    anomaly_score: float
    is_anomaly: bool
    summary_headline: str
    primary_concern: Optional[str] = None
    critical_count: int = 0
    warning_count: int = 0
    recommendations: list[DiagnosticRecommendationSchema] = Field(default_factory=list)


class ModelStatusResponse(BaseModel):
    """Metadata status report for the active ML model."""

    is_trained: bool
    model_name: str
    version: str
    mode: str
    expected_features: int = 39
    training_samples_count: Optional[int] = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)


class AnomalyAuditItemSchema(BaseModel):
    """Structured historical anomaly and telemetry evaluation record."""

    feature_id: int
    metric_id: Optional[int] = None
    timestamp: datetime
    anomaly_score: float
    is_anomaly: bool
    health_score: Optional[float] = None
    risk_category: str
    model_name: str
    is_trained_model: bool
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    disk_percent: Optional[float] = None
    network_kbps: Optional[float] = None


class HistoricalAnomaliesResponse(BaseModel):
    """Historical evaluated anomalies list response."""

    count: int
    limit: int
    anomalies: list[AnomalyAuditItemSchema]
