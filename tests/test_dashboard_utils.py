"""Unit tests for dashboard utility functions and formatting helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.dashboard.utils.formatting import (
    format_bytes,
    format_percent,
    format_throughput,
    format_timestamp,
    get_resource_status,
    get_risk_badge,
)
from app.ml.models import RiskCategory


class TestDashboardFormattingUtils:
    """Test suite for presentation and metric formatting utilities."""

    def test_format_bytes(self) -> None:
        """Verify byte conversion to human-readable units."""
        assert format_bytes(None) == "N/A"
        assert format_bytes("invalid") == "N/A"  # type: ignore[arg-type]
        assert format_bytes(-50) == "0.0 B"
        assert format_bytes(0) == "0.0 B"
        assert format_bytes(512) == "512.0 B"
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(1536 * 1024 * 1024, precision=2) == "1.50 GB"
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"

    def test_format_percent(self) -> None:
        """Verify percentage formatting with custom precisions."""
        assert format_percent(None) == "N/A"
        assert format_percent("bad") == "N/A"  # type: ignore[arg-type]
        assert format_percent(0.0) == "0.0%"
        assert format_percent(45.678) == "45.7%"
        assert format_percent(99.99, precision=2) == "99.99%"
        assert format_percent(100.0) == "100.0%"

    def test_format_throughput(self) -> None:
        """Verify network throughput formatting (KB/s vs MB/s)."""
        assert format_throughput(None) == "N/A"
        assert format_throughput("invalid") == "N/A"  # type: ignore[arg-type]
        assert format_throughput(-10) == "0.0 KB/s"
        assert format_throughput(0.0) == "0.0 KB/s"
        assert format_throughput(512.4) == "512.4 KB/s"
        assert format_throughput(1024.0) == "1.0 MB/s"
        assert format_throughput(2048.5, precision=2) == "2.00 MB/s"

    def test_format_timestamp(self) -> None:
        """Verify datetime formatting in UTC and fallback states."""
        assert format_timestamp(None) == "Never / Unavailable"

        dt = datetime(2026, 10, 1, 14, 30, 45, tzinfo=timezone.utc)
        assert format_timestamp(dt) == "2026-10-01 14:30:45 UTC"
        assert format_timestamp(dt, show_utc=False) == "2026-10-01 14:30:45"

        naive_dt = datetime(2026, 10, 1, 12, 0, 0)
        assert format_timestamp(naive_dt) == "2026-10-01 12:00:00 UTC"

    def test_get_risk_badge(self) -> None:
        """Verify risk badge generation for all RiskCategory members."""
        normal_badge = get_risk_badge(RiskCategory.NORMAL)
        assert normal_badge["label"] == "Normal"
        assert normal_badge["color"] == "#10B981"
        assert normal_badge["icon"] == "🟢"

        low_badge = get_risk_badge(RiskCategory.LOW)
        assert low_badge["label"] == "Low Risk"
        assert low_badge["color"] == "#3B82F6"

        mod_badge = get_risk_badge(RiskCategory.MODERATE)
        assert mod_badge["label"] == "Moderate Risk"
        assert mod_badge["color"] == "#F59E0B"

        high_badge = get_risk_badge(RiskCategory.HIGH)
        assert high_badge["label"] == "High Risk"
        assert high_badge["color"] == "#F97316"

        crit_badge = get_risk_badge(RiskCategory.CRITICAL)
        assert crit_badge["label"] == "Critical Risk"
        assert crit_badge["color"] == "#EF4444"

        # String support and unknown fallback
        str_badge = get_risk_badge("Critical")
        assert str_badge["label"] == "Critical Risk"

        unknown_badge = get_risk_badge("UnrecognizedCategory")
        assert unknown_badge["icon"] == "⚪"

    def test_get_resource_status(self) -> None:
        """Verify resource status mapping across nominal, warning, and critical tiers."""
        assert get_resource_status(None) == ("Unknown", "#6B7280", "⚪")
        assert get_resource_status(45.0) == ("Nominal", "#10B981", "🟢")
        assert get_resource_status(80.0) == ("Warning", "#F59E0B", "🟡")
        assert get_resource_status(88.5) == ("Warning", "#F59E0B", "🟡")
        assert get_resource_status(95.0) == ("Critical", "#EF4444", "🔴")
        assert get_resource_status(99.9) == ("Critical", "#EF4444", "🔴")
