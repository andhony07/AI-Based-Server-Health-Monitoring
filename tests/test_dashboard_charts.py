"""Unit tests for Plotly dashboard chart builders."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.dashboard.charts.builders import (
    build_anomaly_gauge,
    build_anomaly_scatter_chart,
    build_health_gauge,
    build_multi_metric_timeseries,
    build_resource_breakdown_bar,
)
from app.database.models import SystemMetricRecord
from app.ml.models import RiskCategory


class TestDashboardChartBuilders:
    """Test suite for Plotly visualization builders."""

    def test_build_health_gauge_structure(self) -> None:
        """Verify health gauge indicator configuration and color mapping."""
        # Nominal / Normal
        fig_norm = build_health_gauge(85.5, risk_category=RiskCategory.NORMAL)
        assert fig_norm is not None
        assert len(fig_norm.data) == 1
        indicator = fig_norm.data[0]
        assert indicator.type == "indicator"
        assert indicator.value == 85.5
        assert indicator.gauge.axis.range == (0, 100)
        assert indicator.gauge.bar.color == "#10B981"

        # Critical
        fig_crit = build_health_gauge(15.0, risk_category=RiskCategory.CRITICAL)
        assert fig_crit.data[0].gauge.bar.color == "#EF4444"

        # None health score fallback
        fig_none = build_health_gauge(None, risk_category="Unknown")
        assert fig_none.data[0].value == 0.0

    def test_build_anomaly_gauge_structure(self) -> None:
        """Verify anomaly score gauge indicator and decision boundary threshold."""
        fig_nom = build_anomaly_gauge(0.1234, is_anomaly=False)
        assert len(fig_nom.data) == 1
        ind_nom = fig_nom.data[0]
        assert ind_nom.value == 0.1234
        assert ind_nom.gauge.axis.range == (0.0, 1.0)
        assert ind_nom.gauge.bar.color == "#10B981"
        assert ind_nom.gauge.threshold.value == 0.50

        # Anomaly triggered
        fig_anom = build_anomaly_gauge(0.8500, is_anomaly=True)
        assert fig_anom.data[0].gauge.bar.color == "#EF4444"

    def test_build_resource_breakdown_bar(self) -> None:
        """Verify resource comparison bar chart traces and reference lines."""
        now = datetime.now(timezone.utc)
        record = SystemMetricRecord(
            id=1,
            timestamp=now,
            cpu_percent=45.0,
            memory_percent=82.5,
            disk_percent=96.0,
        )

        fig = build_resource_breakdown_bar(record)
        assert len(fig.data) == 1
        bar = fig.data[0]
        assert bar.type == "bar"
        assert list(bar.x) == ["CPU", "Memory (RAM)", "Disk Storage"]
        assert list(bar.y) == [45.0, 82.5, 96.0]
        # Colors should reflect Nominal, Warning, Critical
        assert list(bar.marker.color) == ["#10B981", "#F59E0B", "#EF4444"]

        # Fallback when metric is None
        fig_none = build_resource_breakdown_bar(None)
        assert list(fig_none.data[0].y) == [0.0, 0.0, 0.0]

    def test_build_multi_metric_timeseries(self) -> None:
        """Verify multi-metric time-series plotting and secondary y-axis handling."""
        # Empty records handling
        fig_empty = build_multi_metric_timeseries([])
        assert len(fig_empty.data) == 0
        assert len(fig_empty.layout.annotations) == 1

        now = datetime.now(timezone.utc)
        records = [
            SystemMetricRecord(
                id=1,
                timestamp=now,
                cpu_percent=30.0,
                memory_percent=50.0,
                disk_percent=60.0,
                network_bytes_sent_per_sec=10240.0,
                network_bytes_recv_per_sec=20480.0,
                process_count=120,
            ),
            SystemMetricRecord(
                id=2,
                timestamp=now,
                cpu_percent=40.0,
                memory_percent=55.0,
                disk_percent=60.0,
                network_bytes_sent_per_sec=15360.0,
                network_bytes_recv_per_sec=30720.0,
                process_count=122,
            ),
        ]

        # Standard percentage metrics
        fig_pct = build_multi_metric_timeseries(
            records,
            selected_metrics=["CPU Utilization (%)", "RAM Utilization (%)"],
        )
        assert len(fig_pct.data) == 2
        assert fig_pct.data[0].name == "CPU (%)"
        assert fig_pct.data[1].name == "RAM (%)"

        # Mixed metrics with throughput
        fig_mixed = build_multi_metric_timeseries(
            records,
            selected_metrics=["CPU Utilization (%)", "Network TX (KB/s)", "Active Processes"],
        )
        assert len(fig_mixed.data) == 3

    def test_build_anomaly_scatter_chart(self) -> None:
        """Verify historical anomaly scatter timeline chart generation."""
        # Empty handling
        fig_empty = build_anomaly_scatter_chart([])
        assert len(fig_empty.data) == 0
        assert len(fig_empty.layout.annotations) == 1

        now = datetime.now(timezone.utc)
        anomalies = [
            {
                "timestamp": now,
                "anomaly_score": 0.15,
                "is_anomaly": False,
                "health_score": 92.0,
                "risk_category": "Normal",
                "model_name": "IsolationForestDetector",
                "cpu_percent": 25.0,
                "memory_percent": 45.0,
            },
            {
                "timestamp": now,
                "anomaly_score": 0.88,
                "is_anomaly": True,
                "health_score": 25.0,
                "risk_category": "High",
                "model_name": "IsolationForestDetector",
                "cpu_percent": 92.0,
                "memory_percent": 88.0,
            },
        ]

        fig = build_anomaly_scatter_chart(anomalies)
        assert len(fig.data) == 1
        scatter = fig.data[0]
        assert scatter.type == "scatter"
        assert len(scatter.x) == 2
        assert list(scatter.y) == [0.15, 0.88]
        # Colors should map Normal -> Green, High -> Orange
        assert list(scatter.marker.color) == ["#10B981", "#F97316"]
