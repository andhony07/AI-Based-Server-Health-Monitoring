"""Dashboard formatting and presentation utility functions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Union

from app.ml.models import RiskCategory


def format_bytes(byte_count: Optional[Union[int, float]], precision: int = 1) -> str:
    """Format byte counts into human-readable binary prefix units (B, KB, MB, GB, TB).

    Args:
        byte_count: Raw byte integer or float.
        precision: Decimal points to display.

    Returns:
        Formatted string (e.g., '14.2 GB').
    """
    if byte_count is None:
        return "N/A"
    try:
        val = float(byte_count)
    except (TypeError, ValueError):
        return "N/A"

    if val < 0:
        return "0.0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_idx = 0
    while val >= 1024.0 and unit_idx < len(units) - 1:
        val /= 1024.0
        unit_idx += 1

    return f"{val:.{precision}f} {units[unit_idx]}"


def format_percent(percent_val: Optional[Union[int, float]], precision: int = 1) -> str:
    """Format a percentage value.

    Args:
        percent_val: Percentage value (0.0 to 100.0).
        precision: Decimal points to display.

    Returns:
        Formatted string (e.g., '54.2%').
    """
    if percent_val is None:
        return "N/A"
    try:
        val = float(percent_val)
    except (TypeError, ValueError):
        return "N/A"
    return f"{val:.{precision}f}%"


def format_throughput(kbps_val: Optional[Union[int, float]], precision: int = 1) -> str:
    """Format network throughput in KB/s or MB/s.

    Args:
        kbps_val: Throughput in kilobytes per second.
        precision: Decimal points to display.

    Returns:
        Formatted string (e.g., '850.5 KB/s' or '12.4 MB/s').
    """
    if kbps_val is None:
        return "N/A"
    try:
        val = float(kbps_val)
    except (TypeError, ValueError):
        return "N/A"

    if val < 0:
        return "0.0 KB/s"

    if val >= 1024.0:
        return f"{val / 1024.0:.{precision}f} MB/s"
    return f"{val:.{precision}f} KB/s"


def format_timestamp(dt: Optional[datetime], show_utc: bool = True) -> str:
    """Format a datetime object into a clean standard display string.

    Args:
        dt: Datetime object.
        show_utc: Whether to append 'UTC' to output.

    Returns:
        Formatted string (e.g., '2026-10-01 12:45:00 UTC').
    """
    if dt is None:
        return "Never / Unavailable"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    res = dt.strftime("%Y-%m-%d %H:%M:%S")
    return f"{res} UTC" if show_utc else res


def get_risk_badge(category: Union[RiskCategory, str]) -> dict[str, str]:
    """Retrieve visual presentation attributes for a given risk category.

    Args:
        category: RiskCategory enum or string value.

    Returns:
        Dictionary containing label, hex color, badge background, and status emoji.
    """
    name = category.value if isinstance(category, RiskCategory) else str(category).capitalize()

    badges = {
        "Normal": {
            "label": "Normal",
            "color": "#10B981",  # Emerald Green
            "bg": "#E6F4EA",
            "icon": "🟢",
            "description": "System operating within historical baseline norms.",
        },
        "Low": {
            "label": "Low Risk",
            "color": "#3B82F6",  # Blue
            "bg": "#E8F0FE",
            "icon": "🔵",
            "description": "Mild telemetry variance detected; well within safe operational limits.",
        },
        "Moderate": {
            "label": "Moderate Risk",
            "color": "#F59E0B",  # Amber
            "bg": "#FEF3C7",
            "icon": "🟡",
            "description": "Notable multi-metric variation or moderate resource pressure observed.",
        },
        "High": {
            "label": "High Risk",
            "color": "#F97316",  # Orange
            "bg": "#FFEDD5",
            "icon": "🟠",
            "description": "Elevated anomaly score or severe metric stress. Close inspection recommended.",
        },
        "Critical": {
            "label": "Critical Risk",
            "color": "#EF4444",  # Red
            "bg": "#FEE2E2",
            "icon": "🔴",
            "description": "Extreme behavioral outlier or resource saturation (>=95%). Urgent review required.",
        },
    }
    return badges.get(
        name,
        {
            "label": str(name),
            "color": "#6B7280",
            "bg": "#F3F4F6",
            "icon": "⚪",
            "description": "Status unknown or unavailable.",
        },
    )


def get_resource_status(
    val: Optional[float],
    warn_thresh: float = 80.0,
    crit_thresh: float = 95.0,
) -> tuple[str, str, str]:
    """Determine health status tier and colors for a resource percentage.

    Args:
        val: Percentage value (0.0 - 100.0).
        warn_thresh: Warning threshold.
        crit_thresh: Critical threshold.

    Returns:
        Tuple of (status_label, hex_color, icon).
    """
    if val is None:
        return ("Unknown", "#6B7280", "⚪")
    if val >= crit_thresh:
        return ("Critical", "#EF4444", "🔴")
    if val >= warn_thresh:
        return ("Warning", "#F59E0B", "🟡")
    return ("Nominal", "#10B981", "🟢")
