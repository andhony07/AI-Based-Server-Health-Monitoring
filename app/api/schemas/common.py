"""Common and shared Pydantic response schemas for API endpoints."""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard generic API response envelope."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(default=True, description="Indicates whether the request was successful")
    message: Optional[str] = Field(default=None, description="Optional human-readable status message")
    data: Optional[T] = Field(default=None, description="Response payload")


class ErrorResponse(BaseModel):
    """Standard error response payload."""

    success: bool = Field(default=False)
    detail: str = Field(description="Detailed error explanation")
    error_code: Optional[str] = Field(default=None, description="Domain error code identifier")
    timestamp: Optional[str] = Field(default=None, description="ISO 8601 error generation timestamp")


class StatusResponse(BaseModel):
    """Simple operational status acknowledgement."""

    success: bool = Field(default=True)
    message: str = Field(description="Operational status message")
