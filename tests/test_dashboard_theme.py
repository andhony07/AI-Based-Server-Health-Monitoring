"""Unit and integration tests for the AIOps dashboard theming and design system."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest import mock

import pytest

from app.dashboard.charts.builders import (
    build_anomaly_gauge,
    build_anomaly_scatter_chart,
    build_health_gauge,
    build_multi_metric_timeseries,
    build_resource_breakdown_bar,
)
from app.dashboard.components.diagnostic_card import render_diagnostic_report
from app.dashboard.components.status_header import render_status_header
from app.dashboard.utils.theme import (
    DARK_TOKENS,
    LIGHT_TOKENS,
    ThemeTokens,
    apply_theme_css,
    generate_theme_css,
    get_current_theme,
    get_theme_risk_badge,
    get_theme_tokens,
    set_theme,
)
from app.database.models import SystemMetricRecord
from app.ml.diagnostics import DiagnosticEngine
from app.ml.models import PredictionResult, RiskCategory


class TestDashboardThemingSystem:
    """Test suite for theme tokens, CSS generation, and theme-aware visualizations."""

    def test_theme_tokens_contrast_and_consistency(self) -> None:
        """Verify tokens are populated with distinct, high-contrast values."""
        assert DARK_TOKENS.mode == "dark"
        assert LIGHT_TOKENS.mode == "light"

        # Backgrounds must differ
        assert DARK_TOKENS.bg_app != LIGHT_TOKENS.bg_app
        assert DARK_TOKENS.bg_card != LIGHT_TOKENS.bg_card

        # Text colors must have inverted luminance
        assert DARK_TOKENS.text_primary.startswith("#F")
        assert LIGHT_TOKENS.text_primary.startswith("#0")

        # Accents must be populated
        assert DARK_TOKENS.accent.startswith("#")
        assert LIGHT_TOKENS.accent.startswith("#")

        # All severity colors must match nominal expectations
        for tokens in (DARK_TOKENS, LIGHT_TOKENS):
            assert tokens.color_normal == "#10B981"
            assert tokens.color_low == "#3B82F6"
            assert tokens.color_moderate == "#F59E0B"
            assert tokens.color_high == "#F97316"
            assert tokens.color_critical == "#EF4444"

    def test_get_theme_tokens_retrieval_and_fallbacks(self) -> None:
        """Verify get_theme_tokens handles various case strings and None."""
        assert get_theme_tokens("dark") is DARK_TOKENS
        assert get_theme_tokens("DARK") is DARK_TOKENS
        assert get_theme_tokens("Dark (AIOps)") is DARK_TOKENS

        assert get_theme_tokens("light") is LIGHT_TOKENS
        assert get_theme_tokens("LIGHT") is LIGHT_TOKENS
        assert get_theme_tokens("Light (Enterprise)") is LIGHT_TOKENS

        # None defaults to dark (or session_state value)
        tokens_default = get_theme_tokens(None)
        assert tokens_default in (DARK_TOKENS, LIGHT_TOKENS)

    def test_generate_theme_css_contains_core_variables(self) -> None:
        """Verify generated CSS includes critical variables and component overrides."""
        dark_css = generate_theme_css(DARK_TOKENS)
        assert "<style>" in dark_css
        assert "--bg-app: #0B0F19;" in dark_css
        assert "--bg-card: #151D2C;" in dark_css
        assert "[data-testid=\"stMetric\"]" in dark_css

        light_css = generate_theme_css(LIGHT_TOKENS)
        assert "--bg-app: #F8FAFC;" in light_css
        assert "--bg-card: #FFFFFF;" in light_css

    def test_get_theme_risk_badge(self) -> None:
        """Verify theme-aware risk badge generation for Dark and Light modes."""
        dark_crit = get_theme_risk_badge(RiskCategory.CRITICAL, mode="dark")
        assert dark_crit["color"] == "#EF4444"
        assert "rgba(239, 68, 68" in dark_crit["bg"]

        light_crit = get_theme_risk_badge(RiskCategory.CRITICAL, mode="light")
        assert light_crit["color"] == "#EF4444"
        assert light_crit["bg"] == "#FEE2E2"

        # Explicitly verify theme= keyword argument resolution (both Enum and string category)
        dark_theme_crit = get_theme_risk_badge(RiskCategory.CRITICAL, theme="dark")
        assert dark_theme_crit["bg"] == dark_crit["bg"]

        light_theme_crit = get_theme_risk_badge(RiskCategory.CRITICAL, theme="light")
        assert light_theme_crit["bg"] == light_crit["bg"]

        # String category name support with theme=
        str_dark_crit = get_theme_risk_badge("Critical", theme="dark")
        assert str_dark_crit["color"] == "#EF4444"
        assert "rgba(239, 68, 68" in str_dark_crit["bg"]

        str_light_norm = get_theme_risk_badge("Normal", theme="light")
        assert str_light_norm["color"] == "#10B981"
        assert str_light_norm["bg"] == "#E6F4EA"

    def test_build_health_gauge_with_explicit_themes(self) -> None:
        """Verify health gauge layout adjusts properly for Dark and Light themes."""
        fig_dark = build_health_gauge(85.0, risk_category=RiskCategory.NORMAL, theme="dark")
        assert fig_dark.layout.font.color == DARK_TOKENS.chart_font_color
        assert fig_dark.data[0].gauge.bgcolor == DARK_TOKENS.chart_gauge_bg

        fig_light = build_health_gauge(85.0, risk_category=RiskCategory.NORMAL, theme="light")
        assert fig_light.layout.font.color == LIGHT_TOKENS.chart_font_color
        assert fig_light.data[0].gauge.bgcolor == LIGHT_TOKENS.chart_gauge_bg

    def test_build_anomaly_gauge_with_explicit_themes(self) -> None:
        """Verify anomaly gauge adjusts for Dark and Light themes."""
        fig_dark = build_anomaly_gauge(0.35, is_anomaly=False, theme="dark")
        assert fig_dark.layout.font.color == DARK_TOKENS.chart_font_color
        assert fig_dark.data[0].gauge.axis.tickcolor == DARK_TOKENS.chart_axis_color

        fig_light = build_anomaly_gauge(0.35, is_anomaly=False, theme="light")
        assert fig_light.layout.font.color == LIGHT_TOKENS.chart_font_color
        assert fig_light.data[0].gauge.axis.tickcolor == LIGHT_TOKENS.chart_axis_color

    def test_build_resource_breakdown_bar_with_themes(self) -> None:
        """Verify resource breakdown bar chart font and grid styling."""
        record = SystemMetricRecord(
            id=1,
            timestamp=datetime.now(timezone.utc),
            cpu_percent=60.0,
            memory_percent=70.0,
            disk_percent=80.0,
        )
        fig_dark = build_resource_breakdown_bar(record, theme="dark")
        assert fig_dark.layout.font.color == DARK_TOKENS.chart_font_color
        assert fig_dark.layout.yaxis.gridcolor == DARK_TOKENS.chart_grid_color

        fig_light = build_resource_breakdown_bar(record, theme="light")
        assert fig_light.layout.font.color == LIGHT_TOKENS.chart_font_color
        assert fig_light.layout.yaxis.gridcolor == LIGHT_TOKENS.chart_grid_color

    def test_build_multi_metric_timeseries_with_themes(self) -> None:
        """Verify timeseries chart theming on dark and light modes."""
        now = datetime.now(timezone.utc)
        records = [
            SystemMetricRecord(id=1, timestamp=now, cpu_percent=25.0, memory_percent=40.0, disk_percent=50.0),
            SystemMetricRecord(id=2, timestamp=now, cpu_percent=35.0, memory_percent=42.0, disk_percent=50.0),
        ]
        fig_dark = build_multi_metric_timeseries(records, theme="dark")
        assert fig_dark.layout.font.color == DARK_TOKENS.chart_font_color
        assert fig_dark.layout.xaxis.gridcolor == DARK_TOKENS.chart_grid_color

        fig_light = build_multi_metric_timeseries(records, theme="light")
        assert fig_light.layout.font.color == LIGHT_TOKENS.chart_font_color
        assert fig_light.layout.xaxis.gridcolor == LIGHT_TOKENS.chart_grid_color

    def test_build_anomaly_scatter_chart_with_themes(self) -> None:
        """Verify scatter chart theming on dark and light modes."""
        anomalies = [
            {
                "timestamp": datetime.now(timezone.utc),
                "anomaly_score": 0.22,
                "is_anomaly": False,
                "health_score": 90.0,
                "risk_category": "Normal",
            }
        ]
        fig_dark = build_anomaly_scatter_chart(anomalies, theme="dark")
        assert fig_dark.layout.font.color == DARK_TOKENS.chart_font_color

        fig_light = build_anomaly_scatter_chart(anomalies, theme="light")
        assert fig_light.layout.font.color == LIGHT_TOKENS.chart_font_color

    def test_render_status_header_with_theme(self) -> None:
        """Verify render_status_header executes with theme parameter without error."""
        with (
            mock.patch("streamlit.columns", return_value=[mock.MagicMock(), mock.MagicMock()]),
            mock.patch("streamlit.markdown") as mock_md,
        ):
            render_status_header(
                last_updated=datetime.now(timezone.utc),
                is_monitoring=True,
                model_name="IsolationForestDetector",
                is_model_trained=True,
                db_record_count=100,
                theme="dark",
                overall_status="HEALTHY",
            )
            assert mock_md.called

    def test_render_diagnostic_report_with_theme(self) -> None:
        """Verify render_diagnostic_report executes cleanly with theme parameter."""
        engine = DiagnosticEngine()
        pred = PredictionResult(
            timestamp=datetime.now(timezone.utc),
            is_anomaly=False,
            anomaly_score=0.15,
            raw_decision_score=0.15,
            health_score=92.0,
            risk_category=RiskCategory.NORMAL,
            model_name="IsolationForestDetector",
            model_version="1.0.0",
        )
        report = engine.generate_report(prediction=pred)

        with (
            mock.patch("streamlit.success") as mock_succ,
            mock.patch("streamlit.markdown") as mock_md,
            mock.patch("streamlit.expander", return_value=mock.MagicMock()),
            mock.patch("streamlit.dataframe") as mock_df,
        ):
            render_diagnostic_report(report, theme="dark")
            assert mock_succ.called or mock_md.called
