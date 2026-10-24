"""Pydantic schemas for hardware telemetry, metrics, and collection monitoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class CPUMetricsSchema(BaseModel):
    """CPU telemetry schema."""

    utilization_percent: float = Field(ge=0.0, le=100.0)
    logical_cores: int = Field(ge=1)
    physical_cores: Optional[int] = None
    per_core_percent: list[float] = Field(default_factory=list)


class MemoryMetricsSchema(BaseModel):
    """Memory telemetry schema."""

    total_bytes: int = Field(ge=0)
    available_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    utilization_percent: float = Field(ge=0.0, le=100.0)
    total_mb: Optional[float] = None
    used_mb: Optional[float] = None
    available_mb: Optional[float] = None


class DiskPartitionMetricsSchema(BaseModel):
    """Disk partition telemetry schema."""

    mount_point: str
    total_bytes: int = Field(ge=0)
    used_bytes: int = Field(ge=0)
    free_bytes: int = Field(ge=0)
    utilization_percent: float = Field(ge=0.0, le=100.0)
    device: Optional[str] = None
    fstype: Optional[str] = None
    total_gb: Optional[float] = None
    used_gb: Optional[float] = None
    free_gb: Optional[float] = None


class NetworkMetricsSchema(BaseModel):
    """Network I/O telemetry schema."""

    bytes_sent: int = Field(ge=0)
    bytes_recv: int = Field(ge=0)
    packets_sent: int = Field(ge=0)
    packets_recv: int = Field(ge=0)
    upload_kbps: float = Field(ge=0.0)
    download_kbps: float = Field(ge=0.0)


class ProcessMetricsSchema(BaseModel):
    """Monitored process telemetry schema."""

    pid: int
    name: str
    cpu_percent: float = Field(ge=0.0)
    memory_percent: float = Field(ge=0.0)
    status: Optional[str] = None
    memory_bytes: Optional[int] = None
    num_threads: Optional[int] = None


class SystemMetricRecordSchema(BaseModel):
    """Persisted system metric record schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    cpu_percent: Optional[float] = None
    cpu_logical_cores: Optional[int] = None
    cpu_physical_cores: Optional[int] = None
    memory_total_bytes: Optional[int] = None
    memory_used_bytes: Optional[int] = None
    memory_available_bytes: Optional[int] = None
    memory_percent: Optional[float] = None
    disk_total_bytes: Optional[int] = None
    disk_used_bytes: Optional[int] = None
    disk_free_bytes: Optional[int] = None
    disk_percent: Optional[float] = None
    network_bytes_sent: Optional[int] = None
    network_bytes_recv: Optional[int] = None
    network_bytes_sent_per_sec: Optional[float] = None
    network_bytes_recv_per_sec: Optional[float] = None
    process_count: Optional[int] = None
    top_process_pid: Optional[int] = None
    top_process_name: Optional[str] = None
    top_process_cpu_percent: Optional[float] = None
    top_process_memory_percent: Optional[float] = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class FeatureVectorRecordSchema(BaseModel):
    """Persisted 39-feature vector schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    metric_id: Optional[int] = None
    timestamp: datetime
    features: dict[str, float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class LatestTelemetryResponse(BaseModel):
    """Unified response containing latest metric sample, prediction, and feature vector."""

    metrics: Optional[SystemMetricRecordSchema] = None
    features: Optional[FeatureVectorRecordSchema] = None
    prediction: Optional[dict[str, Any]] = None
    collector_status: str = Field(default="OPERATIONAL")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HistoricalTelemetryResponse(BaseModel):
    """Historical telemetry list response with metadata."""

    count: int
    limit: int
    records: list[SystemMetricRecordSchema]


class SnapshotResponse(BaseModel):
    """Response returned upon capturing an on-demand live telemetry sample."""

    success: bool
    persisted: bool
    metrics: Optional[SystemMetricRecordSchema] = None
    prediction: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class MonitoringStatusResponse(BaseModel):
    """Status of the background telemetry collection worker in the API process."""

    is_running: bool
    sample_interval: float
    message: str
    telemetry_freshness: Optional[str] = None
    seconds_since_last_sample: Optional[float] = None


class MonitoringControlRequest(BaseModel):
    """Request parameters for controlling the background monitoring thread."""

    interval: Optional[float] = Field(
        default=None,
        gt=0.5,
        le=60.0,
        description="Sampling interval in seconds between 0.5 and 60.0",
    )
