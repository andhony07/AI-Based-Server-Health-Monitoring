"""Pydantic schemas for database inspection, validation logs, and platform operational status."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class ValidationLogRecordSchema(BaseModel):
    """Preprocessing validation issue audit record schema."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    metric_id: Optional[int] = None
    timestamp: datetime
    is_valid: bool
    issues_count: int
    has_errors: bool
    issues: list[dict[str, Any]] = Field(default_factory=list)


class DatabaseSummaryResponse(BaseModel):
    """SQLite database storage and record count summary."""

    database_path: str
    database_exists: bool
    file_size_bytes: int
    counts: dict[str, int]
    total_records: int
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    retention_days: Optional[int] = None


class OperationalStatusResponse(BaseModel):
    """Platform-wide operational health status report."""

    timestamp: str
    overall_status: str = Field(description="Platform operational state: HEALTHY, DEGRADED, or CRITICAL")
    status_color: str
    headline: str
    subsystems: dict[str, Any]
