"""Pydantic schemas package for FastAPI request/response validation."""

from __future__ import annotations

from app.api.schemas.common import APIResponse, ErrorResponse, StatusResponse
from app.api.schemas.database import (
    DatabaseSummaryResponse,
    OperationalStatusResponse,
    ValidationLogRecordSchema,
)
from app.api.schemas.ml import (
    AnomalyAuditItemSchema,
    AnomalyResultSchema,
    DiagnosticEvidenceSchema,
    DiagnosticRecommendationSchema,
    DiagnosticReportSchema,
    HealthScoreResultSchema,
    HistoricalAnomaliesResponse,
    ModelStatusResponse,
    PredictionResultSchema,
)
from app.api.schemas.simulation import (
    ScenarioProfileSchema,
    SimulationRunRequest,
    SimulationRunResponse,
)
from app.api.schemas.telemetry import (
    CPUMetricsSchema,
    DiskPartitionMetricsSchema,
    FeatureVectorRecordSchema,
    HistoricalTelemetryResponse,
    LatestTelemetryResponse,
    MemoryMetricsSchema,
    MonitoringControlRequest,
    MonitoringStatusResponse,
    NetworkMetricsSchema,
    ProcessMetricsSchema,
    SnapshotResponse,
    SystemMetricRecordSchema,
)

__all__ = [
    "APIResponse",
    "ErrorResponse",
    "StatusResponse",
    "CPUMetricsSchema",
    "MemoryMetricsSchema",
    "DiskPartitionMetricsSchema",
    "NetworkMetricsSchema",
    "ProcessMetricsSchema",
    "SystemMetricRecordSchema",
    "FeatureVectorRecordSchema",
    "LatestTelemetryResponse",
    "HistoricalTelemetryResponse",
    "SnapshotResponse",
    "MonitoringStatusResponse",
    "MonitoringControlRequest",
    "AnomalyResultSchema",
    "HealthScoreResultSchema",
    "PredictionResultSchema",
    "DiagnosticEvidenceSchema",
    "DiagnosticRecommendationSchema",
    "DiagnosticReportSchema",
    "ModelStatusResponse",
    "AnomalyAuditItemSchema",
    "HistoricalAnomaliesResponse",
    "ScenarioProfileSchema",
    "SimulationRunRequest",
    "SimulationRunResponse",
    "ValidationLogRecordSchema",
    "DatabaseSummaryResponse",
    "OperationalStatusResponse",
]
