"""Interactive Streamlit Web Dashboard for AI-Based Server Health Monitoring.

Provides executive telemetry overview, live monitoring controls,
Isolation Forest anomaly visualization, historical trends, and database inspection.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import Settings, get_settings
from app.dashboard.charts.builders import (
    build_anomaly_scatter_chart,
    build_multi_metric_timeseries,
    build_resource_breakdown_bar,
    build_simulation_comparison_bar,
)
from app.dashboard.components.diagnostic_card import render_diagnostic_report
from app.dashboard.components.health_card import render_health_and_risk
from app.dashboard.components.metrics_cards import render_metric_cards
from app.dashboard.components.status_header import render_status_header
from app.dashboard.services.dashboard_service import DashboardService
from app.dashboard.utils.formatting import format_bytes, format_percent, format_timestamp, get_risk_badge
from app.dashboard.utils.theme import apply_theme_css, get_theme_risk_badge, get_theme_tokens
from app.ml.simulation import SCENARIO_PROFILES, SimulationScenario



# -----------------------------------------------------------------------------
# Page Configuration & Initialization
# -----------------------------------------------------------------------------

def configure_page() -> None:
    """Configure Streamlit page title and layout safely."""
    try:
        st.set_page_config(
            page_title="Server Health & Failure Risk Monitor",
            page_icon="🖥️",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except Exception:
        # Ignore if called outside Streamlit context or already configured
        pass


@st.cache_resource
def get_dashboard_service() -> DashboardService:
    """Instantiate and cache a shared DashboardService coordinator."""
    return DashboardService()


def main() -> None:
    """Main dashboard application flow."""
    configure_page()
    service = get_dashboard_service()
    if not hasattr(service, "run_simulation") or not hasattr(service, "get_operational_status"):
        # Invalidate stale in-memory cached instance from prior Streamlit hot-reload
        get_dashboard_service.clear()
        service = get_dashboard_service()
    settings: Settings = service.settings


    # -------------------------------------------------------------------------
    # Sidebar: Product Identity, Navigation & Live Operational Controls
    # -------------------------------------------------------------------------
    with st.sidebar:
        # Product Identity Area
        st.markdown(
            """<div style="padding: 4px 0 14px 0; border-bottom: 1px solid #293548; margin-bottom: 14px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="background: rgba(56, 189, 248, 0.16); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 800; letter-spacing: 0.8px;">AIOPS</span>
                    <span style="font-size: 11px; color: #94A3B8; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px;">Operations Center</span>
                </div>
                <h3 style="margin: 0 0 2px 0; font-size: 16px; font-weight: 700; color: #F8FAFC; letter-spacing: -0.3px; line-height: 1.3;">
                    AI Based Server Health Monitoring
                </h3>
                <p style="margin: 0; font-size: 11px; color: #64748B;">Telemetry Inference &amp; Failure Risk</p>
            </div>""",
            unsafe_allow_html=True,
        )

        # Primary Navigation Hierarchy
        st.markdown("<div style='font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;'>Navigation</div>", unsafe_allow_html=True)
        page = st.radio(
            label="Select View",
            options=[
                "📊 System Overview",
                "🛡️ Health & Risk Analysis",
                "🧪 Anomaly Simulation",
                "⚡ Real-Time Monitoring",
                "📈 Historical Telemetry",
                "🔍 Anomaly Audit Log",
                "🗄️ Database & Operational Status",
            ],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("<hr style='margin:14px 0; border:none; border-top:1px solid #293548;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:10px;'>Live Controls</div>", unsafe_allow_html=True)

        # Snapshot button
        if st.button("📸 Capture Live Snapshot", width="stretch", type="primary"):
            with st.spinner("Capturing live telemetry sample..."):
                _, pred, err = service.capture_live_snapshot(persist=True)
                if err:
                    st.error(f"Snapshot error: {err}")
                else:
                    st.success("Telemetry sample persisted & evaluated!")
                    st.rerun()

        # Background monitoring toggle
        is_bg_running = service.is_background_monitoring_running()
        if is_bg_running:
            if st.button("⏹️ Stop Background Worker", width="stretch"):
                service.stop_background_monitoring()
                st.info("Stopped background monitoring thread.")
                st.rerun()
        else:
            if st.button("▶️ Start Background Worker", width="stretch"):
                service.start_background_monitoring()
                st.success("Started background monitoring thread.")
                st.rerun()

        # Auto-refresh control
        auto_refresh = st.checkbox("Auto-refresh page", value=False)
        refresh_interval = st.slider(
            "Refresh Interval (seconds)",
            min_value=2,
            max_value=30,
            value=settings.dashboard_refresh_interval,
            step=1,
            disabled=not auto_refresh,
        )

        if st.button("🔄 Refresh Now", width="stretch"):
            st.rerun()

        st.markdown("<hr style='margin:14px 0; border:none; border-top:1px solid #293548;'>", unsafe_allow_html=True)
        # System & Model metadata in sidebar
        is_model_trained = service.prediction_service.is_model_ready()
        model_name = service.prediction_service.model_name
        summary = service.get_database_summary()

        st.markdown("<div style='font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;'>Runtime &amp; Storage Engine</div>", unsafe_allow_html=True)
        st.caption(f"**ML Engine:** `{model_name}`")
        st.caption(f"**ML Status:** {'🟢 Trained Artifact' if is_model_trained else '⚠️ Heuristic Baseline'}")
        st.caption(f"**Collector Worker:** {'🟢 Active' if is_bg_running else '⚪ Idle'}")
        st.caption(f"**SQLite Persistence:** `{summary['counts']['system_metrics']:,}` samples")

    # Dark mode is the sole user-facing theme for this AIOps Command Center redesign
    active_theme = "dark"
    st.session_state["theme"] = active_theme
    apply_theme_css(active_theme)
    tokens = get_theme_tokens(active_theme)

    # -------------------------------------------------------------------------
    # Shared Data Loading
    # -------------------------------------------------------------------------
    latest_metric = service.get_latest_metrics()
    latest_pred = service.get_latest_prediction()
    last_ts = latest_metric.timestamp if latest_metric else None

    # Derive active section title
    section_name = page.split(" ", 1)[-1] if " " in page else page

    # Render top status header on all pages
    render_status_header(
        last_updated=last_ts,
        is_monitoring=service.is_background_monitoring_running(),
        model_name=service.prediction_service.model_name,
        is_model_trained=service.prediction_service.is_model_ready(),
        db_record_count=summary["counts"]["system_metrics"],
        theme="dark",
        section_title=section_name,
    )

    # -------------------------------------------------------------------------
    # Page 1: System Overview
    # -------------------------------------------------------------------------
    if page == "📊 System Overview":
        # Section Header
        st.markdown(
            f"""<div style='margin-bottom:14px;'>
                <h3 style='margin:0 0 4px 0; font-size:18px; font-weight:700; color:{tokens.text_primary};'>System Overview &amp; Telemetry Command Center</h3>
                <p style='margin:0; font-size:12px; color:{tokens.text_secondary};'>Real-time hardware saturation telemetry, machine learning anomaly assessment, and recent ingestion log</p>
            </div>""",
            unsafe_allow_html=True,
        )

        # KPI Row: 5 Metric Cards
        render_metric_cards(latest_metric, theme="dark")

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        # Primary Monitoring Area & Operational Assessment
        col_res, col_quick_health = st.columns([1.6, 1.4])

        with col_res:
            st.markdown(
                f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;'>"
                f"Hardware Resource Saturation Breakdown</div>",
                unsafe_allow_html=True,
            )
            if latest_metric is not None:
                fig_bar = build_resource_breakdown_bar(latest_metric, theme="dark")
                st.plotly_chart(fig_bar, width="stretch")
            else:
                st.markdown(
                    f"""<div class="aiops-empty-state">
                        <div style="font-size:24px;">📊</div>
                        <div class="title">Resource Saturation Unavailable</div>
                        <div class="desc">No active telemetry readings have been recorded. Click "Capture Live Snapshot" in the sidebar to acquire initial hardware readings.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        with col_quick_health:
            st.markdown(
                f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;'>"
                f"Operational Health &amp; Failure Risk Assessment</div>",
                unsafe_allow_html=True,
            )
            if latest_pred is not None:
                badge = get_theme_risk_badge(latest_pred.risk_category, theme="dark")
                health_val = f"{latest_pred.health_score:.1f} / 100" if latest_pred.health_score is not None else "N/A"
                decision_status = "⚠️ Statistical Outlier" if latest_pred.is_anomaly else "🟢 Nominal Cluster"
                decision_color = tokens.color_critical if latest_pred.is_anomaly else tokens.color_normal

                warning_html = ""
                if latest_pred.warnings:
                    items = "".join([f"<li style='margin-bottom:3px;'>{w}</li>" for w in latest_pred.warnings])
                    warning_html = (
                        f"<div style='margin-top:12px; padding:10px 12px; background-color:{tokens.bg_card_secondary}; border-left:3px solid {tokens.color_moderate}; border-radius:4px; font-size:11px; color:{tokens.text_secondary};'>"
                        f"<b style='color:{tokens.color_moderate};'>Active Signal Deductions:</b>"
                        f"<ul style='margin:4px 0 0 16px; padding:0;'>{items}</ul>"
                        f"</div>"
                    )

                overview_card_html = (
                    f"<div style='background-color:{tokens.bg_card}; border:1px solid {tokens.border_color}; padding:18px; border-radius:8px; box-sizing:border-box;'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;'>"
                    f"<div>"
                    f"<div style='font-size:11px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px;'>Composite Health Score</div>"
                    f"<div style='font-size:30px; font-weight:800; color:{badge['color']}; font-variant-numeric:tabular-nums; margin-top:2px;'>{health_val}</div>"
                    f"</div>"
                    f"<div style='text-align:right;'>"
                    f"<div style='font-size:11px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px;'>Risk Assessment</div>"
                    f"<div style='display:inline-flex; align-items:center; background-color:{badge['bg']}; color:{badge['color']}; border:1px solid {badge['color']}40; padding:4px 10px; border-radius:4px; font-size:12px; font-weight:700; margin-top:4px;'>"
                    f"{badge['icon']} {badge['label']}"
                    f"</div>"
                    f"</div>"
                    f"</div>"
                    f"<div style='display:grid; grid-template-columns: 1fr 1fr; gap:10px; padding:10px 12px; background-color:{tokens.bg_card_secondary}; border-radius:6px; border:1px solid {tokens.border_color};'>"
                    f"<div>"
                    f"<span style='font-size:11px; color:{tokens.text_muted}; text-transform:uppercase; font-weight:600;'>Anomaly Score:</span><br>"
                    f"<span style='font-size:15px; font-weight:700; color:{tokens.text_primary}; font-variant-numeric:tabular-nums;'>{latest_pred.anomaly_score:.4f}</span>"
                    f"</div>"
                    f"<div>"
                    f"<span style='font-size:11px; color:{tokens.text_muted}; text-transform:uppercase; font-weight:600;'>Cluster Boundary:</span><br>"
                    f"<span style='font-size:12px; font-weight:700; color:{decision_color};'>{decision_status}</span>"
                    f"</div>"
                    f"</div>"
                    f"<div style='font-size:12px; color:{tokens.text_secondary}; margin-top:12px; line-height:1.4;'>"
                    f"{badge['description']}"
                    f"</div>"
                    f"{warning_html}"
                    f"<hr style='margin:12px 0 8px 0; border:none; border-top:1px solid {tokens.border_color};'>"
                    f"<div style='display:flex; justify-content:space-between; font-size:11px; color:{tokens.text_muted};'>"
                    f"<span>Evaluated by: <b style='color:{tokens.text_secondary};'>{latest_pred.model_name} (v{latest_pred.model_version})</b></span>"
                    f"<span>Time: <b style='color:{tokens.text_secondary};'>{format_timestamp(latest_pred.timestamp)}</b></span>"
                    f"</div>"
                    f"</div>"
                )
                st.markdown(overview_card_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    f"""<div class="aiops-empty-state">
                        <div style="font-size:24px;">🛡️</div>
                        <div class="title">Health Evaluation Unavailable</div>
                        <div class="desc">No machine learning health predictions have been evaluated yet. Click "Capture Live Snapshot" in the sidebar to run ML inference.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Recent 5 telemetry samples table
        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;'>"
            f"Recent Telemetry Ingestion Log</div>",
            unsafe_allow_html=True,
        )
        recent_samples = service.get_historical_metrics(limit=5)
        if recent_samples:
            df_recent = pd.DataFrame(
                [
                    {
                        "ID": s.id,
                        "Timestamp (UTC)": format_timestamp(s.timestamp),
                        "CPU %": f"{s.cpu_percent:.1f}%" if s.cpu_percent is not None else "N/A",
                        "RAM %": f"{s.memory_percent:.1f}%" if s.memory_percent is not None else "N/A",
                        "Disk %": f"{s.disk_percent:.1f}%" if s.disk_percent is not None else "N/A",
                        "Net TX": f"{(s.network_bytes_sent_per_sec or 0.0)/1024.0:.1f} KB/s",
                        "Net RX": f"{(s.network_bytes_recv_per_sec or 0.0)/1024.0:.1f} KB/s",
                        "Processes": s.process_count if s.process_count is not None else "N/A",
                        "Top Process": f"{s.top_process_name} ({s.top_process_cpu_percent or 0.0:.1f}%)" if s.top_process_name else "N/A",
                    }
                    for s in reversed(recent_samples)
                ]
            )
            st.dataframe(df_recent, width="stretch", hide_index=True)
        else:
            st.markdown(
                f"""<div class="aiops-empty-state">
                    <div style="font-size:24px;">🗄️</div>
                    <div class="title">No Ingestion Records Found</div>
                    <div class="desc">No recent telemetry samples have been persisted into SQLite yet.</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # Page 2: Health & Risk Analysis
    # -------------------------------------------------------------------------
    elif page == "🛡️ Health & Risk Analysis":
        # Section Header
        st.markdown(
            (
                f"<div style='margin-bottom:14px;'>"
                f"<h3 style='margin:0 0 4px 0; font-size:18px; font-weight:700; color:{tokens.text_primary};'>Health &amp; Risk Command Center</h3>"
                f"<p style='margin:0; font-size:12px; color:{tokens.text_secondary};'>Real-time composite health scoring, unsupervised anomaly boundary evaluation, multi-tier risk taxonomy, and explainable root-cause diagnostics</p>"
                f"</div>"
            ),
            unsafe_allow_html=True,
        )

        # Executive Health Summary Ribbon
        if latest_pred is not None:
            badge = get_theme_risk_badge(latest_pred.risk_category, theme="dark")
            health_str = f"{latest_pred.health_score:.1f}" if latest_pred.health_score is not None else "N/A"
            health_color = badge["color"]
            anomaly_str = f"{latest_pred.anomaly_score:.4f}"
            anomaly_status = "⚠️ Outlier Detected" if latest_pred.is_anomaly else "🟢 Nominal Baseline"
            anomaly_status_color = tokens.color_critical if latest_pred.is_anomaly else tokens.color_normal

            # Telemetry indicators
            if latest_metric is not None:
                cpu_val = f"{latest_metric.cpu_percent:.1f}%" if latest_metric.cpu_percent is not None else "N/A"
                ram_val = f"{latest_metric.memory_percent:.1f}%" if latest_metric.memory_percent is not None else "N/A"
                disk_val = f"{latest_metric.disk_percent:.1f}%" if latest_metric.disk_percent is not None else "N/A"
                net_tx = f"{(latest_metric.network_bytes_sent_per_sec or 0.0)/1024.0:.1f} KB/s"
                net_rx = f"{(latest_metric.network_bytes_recv_per_sec or 0.0)/1024.0:.1f} KB/s"
                net_val = f"TX {net_tx} | RX {net_rx}"

                cpu_color = tokens.color_critical if (latest_metric.cpu_percent or 0) >= 85 else (tokens.color_moderate if (latest_metric.cpu_percent or 0) >= 70 else tokens.accent)
                ram_color = tokens.color_critical if (latest_metric.memory_percent or 0) >= 85 else (tokens.color_moderate if (latest_metric.memory_percent or 0) >= 70 else tokens.accent)
                disk_color = tokens.color_critical if (latest_metric.disk_percent or 0) >= 90 else (tokens.color_moderate if (latest_metric.disk_percent or 0) >= 80 else tokens.accent)

                telemetry_chips_html = (
                    f"<div style='display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin-top:12px; padding-top:12px; border-top:1px solid {tokens.border_color};'>"
                    f"<div style='background-color:{tokens.bg_card_secondary}; padding:8px 12px; border-radius:6px; border:1px solid {tokens.border_color};'>"
                    f"<div style='font-size:10px; color:{tokens.text_muted}; text-transform:uppercase; font-weight:700;'>Host CPU Saturation</div>"
                    f"<div style='font-size:15px; font-weight:800; color:{cpu_color}; font-variant-numeric:tabular-nums; margin-top:2px;'>{cpu_val}</div>"
                    f"</div>"
                    f"<div style='background-color:{tokens.bg_card_secondary}; padding:8px 12px; border-radius:6px; border:1px solid {tokens.border_color};'>"
                    f"<div style='font-size:10px; color:{tokens.text_muted}; text-transform:uppercase; font-weight:700;'>RAM Utilization</div>"
                    f"<div style='font-size:15px; font-weight:800; color:{ram_color}; font-variant-numeric:tabular-nums; margin-top:2px;'>{ram_val}</div>"
                    f"</div>"
                    f"<div style='background-color:{tokens.bg_card_secondary}; padding:8px 12px; border-radius:6px; border:1px solid {tokens.border_color};'>"
                    f"<div style='font-size:10px; color:{tokens.text_muted}; text-transform:uppercase; font-weight:700;'>Storage Partition</div>"
                    f"<div style='font-size:15px; font-weight:800; color:{disk_color}; font-variant-numeric:tabular-nums; margin-top:2px;'>{disk_val}</div>"
                    f"</div>"
                    f"<div style='background-color:{tokens.bg_card_secondary}; padding:8px 12px; border-radius:6px; border:1px solid {tokens.border_color};'>"
                    f"<div style='font-size:10px; color:{tokens.text_muted}; text-transform:uppercase; font-weight:700;'>Network Throughput</div>"
                    f"<div style='font-size:12px; font-weight:700; color:{tokens.text_primary}; font-variant-numeric:tabular-nums; margin-top:4px;'>{net_val}</div>"
                    f"</div>"
                    f"</div>"
                )
            else:
                telemetry_chips_html = (
                    f"<div style='margin-top:12px; padding-top:10px; border-top:1px solid {tokens.border_color}; font-size:11px; color:{tokens.text_muted};'>"
                    f"Hardware Telemetry Stream: <i>No sensor readings recorded yet.</i>"
                    f"</div>"
                )

            exec_summary_html = (
                f"<div style='background-color:{tokens.bg_card}; border:1px solid {tokens.border_color}; border-left:5px solid {badge['color']}; padding:16px 20px; border-radius:8px; margin-bottom:16px; box-sizing:border-box;'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;'>"
                f"<div style='display:flex; align-items:center; gap:24px;'>"
                f"<div>"
                f"<div style='font-size:10px; font-weight:700; color:{tokens.text_muted}; text-transform:uppercase; letter-spacing:0.6px;'>Overall System Health</div>"
                f"<div style='font-size:26px; font-weight:800; color:{health_color}; font-variant-numeric:tabular-nums;'>"
                f"{health_str} <span style='font-size:14px; font-weight:500; color:{tokens.text_muted};'>/ 100</span>"
                f"</div>"
                f"</div>"
                f"<div style='border-left:1px solid {tokens.border_color}; height:36px;'></div>"
                f"<div>"
                f"<div style='font-size:10px; font-weight:700; color:{tokens.text_muted}; text-transform:uppercase; letter-spacing:0.6px;'>Calibrated Anomaly Score</div>"
                f"<div style='font-size:22px; font-weight:800; color:{tokens.text_primary}; font-variant-numeric:tabular-nums;'>"
                f"{anomaly_str}"
                f"</div>"
                f"</div>"
                f"<div style='border-left:1px solid {tokens.border_color}; height:36px;'></div>"
                f"<div>"
                f"<div style='font-size:10px; font-weight:700; color:{tokens.text_muted}; text-transform:uppercase; letter-spacing:0.6px;'>Cluster Boundary</div>"
                f"<div style='font-size:14px; font-weight:700; color:{anomaly_status_color}; margin-top:4px;'>"
                f"{anomaly_status}"
                f"</div>"
                f"</div>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-size:10px; font-weight:700; color:{tokens.text_muted}; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:4px;'>Risk Classification</div>"
                f"<div style='display:inline-flex; align-items:center; gap:6px; background-color:{badge['bg']}; color:{badge['color']}; border:1px solid {badge['color']}40; padding:4px 12px; border-radius:4px; font-size:13px; font-weight:800;'>"
                f"{badge['icon']} {badge['label']}"
                f"</div>"
                f"</div>"
                f"</div>"
                f"{telemetry_chips_html}"
                f"<div style='display:flex; justify-content:space-between; font-size:11px; color:{tokens.text_muted}; margin-top:10px; padding-top:8px; border-top:1px solid {tokens.border_color};'>"
                f"<span>Evaluated by: <b style='color:{tokens.text_secondary};'>{latest_pred.model_name} (v{latest_pred.model_version})</b></span>"
                f"<span>Inference Timestamp: <b style='color:{tokens.text_secondary};'>{format_timestamp(latest_pred.timestamp)}</b></span>"
                f"</div>"
                f"</div>"
            )
            st.markdown(exec_summary_html, unsafe_allow_html=True)
        else:
            st.markdown(
                (
                    f"<div class=\"aiops-empty-state\" style='margin-bottom:16px;'>"
                    f"<div style=\"font-size:24px;\">🛡️</div>"
                    f"<div class=\"title\">Executive Health Evaluation Unavailable</div>"
                    f"<div class=\"desc\">No active machine learning inference record found. Ingest live telemetry or trigger an anomaly simulation to compute composite health and failure risk.</div>"
                    f"</div>"
                ),
                unsafe_allow_html=True,
            )

        # Health and Anomaly Visualizations (Dual Radial Gauges + Assessment Card)
        render_health_and_risk(
            prediction=latest_pred,
            is_model_trained=service.prediction_service.is_model_ready(),
            theme="dark",
        )

        st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:10px;'>"
            f"Five-Tier Operational Risk Categorization Matrix</div>",
            unsafe_allow_html=True,
        )

        tier_cols = st.columns(5)
        tiers = [
            ("Normal", "< 0.35", "80 - 100", "#10B981", "Nominal telemetry pattern matching training baseline."),
            ("Low", "0.35 - 0.55", "65 - 79", "#38BDF8", "Mild metric variance; well within normal parameters."),
            ("Moderate", "0.55 - 0.75", "45 - 64", "#F59E0B", "Noticeable divergence from normal baseline cluster."),
            ("High", "0.75 - 0.90", "25 - 44", "#F97316", "Significant behavioral outlier; review workload/processes."),
            ("Critical", "≥ 0.90", "0 - 24", "#EF4444", "Severe anomaly or hardware saturation ≥95%."),
        ]

        active_cat = latest_pred.risk_category.value if latest_pred else ""

        for idx, (name, thresh, health, col, desc) in enumerate(tiers):
            with tier_cols[idx]:
                is_active = active_cat == name
                badge_info = get_theme_risk_badge(name, theme="dark")
                border_style = f"2px solid {col}" if is_active else f"1px solid {tokens.border_color}"
                bg_style = badge_info["bg"] if is_active else tokens.bg_card
                shadow_style = f"box-shadow: 0 0 12px {col}30;" if is_active else ""
                active_badge = (
                    f"<span style='background:{col}; color:#FFF; font-size:10px; padding:2px 6px; border-radius:3px; font-weight:800; letter-spacing:0.5px;'>ACTIVE TIER</span>"
                    if is_active
                    else f"<span style='background:{tokens.bg_card_secondary}; color:{tokens.text_muted}; font-size:10px; padding:2px 5px; border-radius:3px; font-weight:600;'>STANDBY</span>"
                )

                card_html = (
                    f"<div style='border:{border_style}; background-color:{bg_style}; {shadow_style} padding:14px; border-radius:8px; height:185px; box-sizing:border-box; display:flex; flex-direction:column; justify-content:space-between;'>"
                    f"<div>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;'>"
                    f"<span style='color:{col}; font-size:14px; font-weight:800; display:flex; align-items:center; gap:4px;'>● {name}</span>"
                    f"{active_badge}"
                    f"</div>"
                    f"<div style='font-size:11px; color:{tokens.text_secondary}; margin-top:4px;'><b>Anomaly:</b> <span style='color:{tokens.text_primary}; font-variant-numeric:tabular-nums;'>{thresh}</span></div>"
                    f"<div style='font-size:11px; color:{tokens.text_secondary};'><b>Health:</b> <span style='color:{tokens.text_primary}; font-variant-numeric:tabular-nums;'>{health}</span></div>"
                    f"</div>"
                    f"<p style='font-size:11px; color:{tokens.text_muted}; margin:8px 0 0 0; line-height:1.3;'>{desc}</p>"
                    f"</div>"
                )
                st.markdown(card_html, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        diag_report = service.get_diagnostics_for_latest()
        render_diagnostic_report(diag_report, theme="dark")

    # -------------------------------------------------------------------------
    # Page: Anomaly Simulation
    # -------------------------------------------------------------------------
    elif page == "🧪 Anomaly Simulation":
        st.markdown(
            '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">'
            '<div>'
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="background:rgba(56, 189, 248, 0.16); color:#38BDF8; border:1px solid rgba(56, 189, 248, 0.4); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:0.8px;">SIMULATION WORKSPACE</span>'
            '<span style="font-size:12px; color:#94A3B8; text-transform:uppercase; font-weight:600; letter-spacing:0.5px;">Deterministic Anomaly Injection Lab</span>'
            '</div>'
            '<h2 style="margin:4px 0 2px 0; font-size:22px; font-weight:700; color:#F8FAFC;">Scenario-Based Fault &amp; Anomaly Simulation</h2>'
            '<p style="margin:0; font-size:13px; color:#94A3B8;">Synthetically generates reproducible, physically-valid telemetry anomaly profiles and executes them through the 39-feature preprocessing pipeline and ML models. Absolutely no physical OS-level fault injection or hardware stress is performed.</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        col_scen, col_opts = st.columns([1.6, 1.0])

        with col_scen:
            scenarios = list(SCENARIO_PROFILES.keys())
            scenario_labels = [f"{SCENARIO_PROFILES[s].name} — ({SCENARIO_PROFILES[s].stress_subsystem})" for s in scenarios]
            selected_idx = st.selectbox(
                "Select Deterministic Anomaly Scenario Profile",
                options=range(len(scenarios)),
                format_func=lambda i: scenario_labels[i],
                index=1,  # Default to CPU Thread Runaway
            )
            selected_scenario = scenarios[selected_idx]
            profile = SCENARIO_PROFILES[selected_scenario]

            risk_b = get_theme_risk_badge(profile.expected_risk)
            outlier_label = "YES (Expected Outlier)" if profile.is_anomaly_expected else "NO (Nominal Inlier)"
            outlier_color = "#EF4444" if profile.is_anomaly_expected else "#10B981"

            dossier_html = (
                f'<div class="aiops-metric-card" style="margin-top:8px; border-left:3px solid #38BDF8;">'
                f'<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">'
                f'<span style="font-size:11px; font-weight:700; color:#38BDF8; text-transform:uppercase; letter-spacing:0.6px;">Scenario Profile Dossier</span>'
                f'<span style="font-size:11px; color:#94A3B8; background:#111827; padding:2px 7px; border-radius:3px; border:1px solid #293548;">Target: {profile.stress_subsystem}</span>'
                f'</div>'
                f'<div style="font-size:14px; font-weight:600; color:#F8FAFC; margin-bottom:6px;">{profile.description}</div>'
                f'<div style="display:flex; gap:16px; font-size:12px; color:#94A3B8; padding-top:6px; border-top:1px solid #293548;">'
                f'<div>Expected Risk: <span style="font-weight:700; color:{risk_b["color"]};">{risk_b["icon"]} {risk_b["label"]}</span></div>'
                f'<div>Anomaly Outlier: <span style="font-weight:700; color:{outlier_color};">{outlier_label}</span></div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(dossier_html, unsafe_allow_html=True)

        with col_opts:
            st.markdown(
                '<div style="font-size:12px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;">Execution Parameters</div>',
                unsafe_allow_html=True,
            )
            sim_seed = st.number_input("Deterministic Random Seed", min_value=1, max_value=99999, value=42, step=1)
            persist_sim = st.checkbox("Commit Sample to SQLite", value=False, help="Persist the generated telemetry and 39-feature vector into the database.")
            run_sim = st.button("🚀 Run Anomaly Simulation", type="primary", width="stretch")

        if run_sim or "last_sim_result" in st.session_state:
            if run_sim:
                with st.spinner("Executing deterministic simulation through ML pipeline..."):
                    sim_res, sim_diag = service.run_simulation(
                        scenario=selected_scenario,
                        persist=persist_sim,
                        seed=int(sim_seed),
                    )
                    st.session_state["last_sim_result"] = sim_res
                    st.session_state["last_sim_diag"] = sim_diag
                    st.session_state["last_sim_seed"] = int(sim_seed)
            else:
                sim_res = st.session_state["last_sim_result"]
                sim_diag = st.session_state["last_sim_diag"]

            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

            if sim_res.persisted:
                st.success(f"Sample successfully committed to SQLite! (Metric ID: #{sim_res.metric_id}, Feature ID: #{sim_res.feature_id})")

            # Executive Simulation Assessment Banner
            pred = sim_res.prediction
            badge = get_theme_risk_badge(pred.risk_category)
            status_text = "ANOMALOUS OUTLIER DETECTED" if pred.is_anomaly else "NOMINAL INLIER VERIFIED"
            status_accent = "#EF4444" if pred.is_anomaly else "#10B981"

            banner_html = (
                f'<div class="aiops-metric-card" style="border-left:4px solid {status_accent}; margin-bottom:16px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">'
                f'<div>'
                f'<div style="font-size:11px; font-weight:700; color:{status_accent}; text-transform:uppercase; letter-spacing:0.8px;">Execution Assessment &bull; {status_text}</div>'
                f'<div style="font-size:18px; font-weight:700; color:#F8FAFC; margin-top:3px;">Simulation Report: {sim_res.profile.name}</div>'
                f'<div style="font-size:12px; color:#94A3B8; margin-top:2px;">Deterministic seed: <code>{st.session_state.get("last_sim_seed", 42)}</code> &nbsp;|&nbsp; Target Subsystem: <code>{sim_res.profile.stress_subsystem}</code></div>'
                f'</div>'
                f'<div style="display:flex; gap:14px; align-items:center;">'
                f'<div style="text-align:right;"><div style="font-size:11px; color:#94A3B8;">Health Score</div><div style="font-size:18px; font-weight:700; color:#F8FAFC;">{pred.health_score:.1f}/100</div></div>'
                f'<div style="text-align:right;"><div style="font-size:11px; color:#94A3B8;">Anomaly Score</div><div style="font-size:18px; font-weight:700; color:{status_accent};">{pred.anomaly_score:.4f}</div></div>'
                f'<div style="text-align:right;"><div style="font-size:11px; color:#94A3B8;">Risk Tier</div><div style="font-size:15px; font-weight:700; color:{badge["color"]};">{badge["icon"]} {badge["label"]}</div></div>'
                f'</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(banner_html, unsafe_allow_html=True)

            # Baseline vs. Simulated Comparison
            baseline_metrics = service.simulator.generate_metrics(
                SimulationScenario.NOMINAL,
                seed=st.session_state.get("last_sim_seed", 42),
            )

            st.markdown("#### Baseline vs. Simulated Hardware Telemetry")
            fig_comp = build_simulation_comparison_bar(
                baseline_metrics=baseline_metrics,
                simulated_metrics=sim_res.metrics,
                scenario_name=sim_res.profile.name,
                theme="dark",
            )
            st.plotly_chart(fig_comp, width="stretch")

            # Subsystem Delta Grid
            d_cpu = sim_res.metrics.cpu.utilization_percent - baseline_metrics.cpu.utilization_percent
            d_ram = sim_res.metrics.memory.utilization_percent - baseline_metrics.memory.utilization_percent
            d_disk = sim_res.metrics.disk.utilization_percent - baseline_metrics.disk.utilization_percent
            d_net_tx = (sim_res.metrics.network.bytes_sent_per_sec - baseline_metrics.network.bytes_sent_per_sec) / 1024.0

            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            with col_d1:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">CPU Utilization</div>'
                    f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{sim_res.metrics.cpu.utilization_percent:.1f}%</div>'
                    f'<div style="font-size:11px; color:{"#EF4444" if d_cpu > 0 else "#10B981"}; margin-top:2px;">{"+" if d_cpu > 0 else ""}{d_cpu:.1f}% vs. Baseline ({baseline_metrics.cpu.utilization_percent:.1f}%)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_d2:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Memory Utilization</div>'
                    f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{sim_res.metrics.memory.utilization_percent:.1f}%</div>'
                    f'<div style="font-size:11px; color:{"#EF4444" if d_ram > 0 else "#10B981"}; margin-top:2px;">{"+" if d_ram > 0 else ""}{d_ram:.1f}% vs. Baseline ({baseline_metrics.memory.utilization_percent:.1f}%)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_d3:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Storage Utilization</div>'
                    f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{sim_res.metrics.disk.utilization_percent:.1f}%</div>'
                    f'<div style="font-size:11px; color:{"#EF4444" if d_disk > 0 else "#10B981"}; margin-top:2px;">{"+" if d_disk > 0 else ""}{d_disk:.1f}% vs. Baseline ({baseline_metrics.disk.utilization_percent:.1f}%)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_d4:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Network Egress</div>'
                    f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{(sim_res.metrics.network.bytes_sent_per_sec / 1024):,.1f} <span style="font-size:12px; color:#94A3B8;">KB/s</span></div>'
                    f'<div style="font-size:11px; color:{"#EF4444" if d_net_tx > 0 else "#10B981"}; margin-top:2px;">{"+" if d_net_tx > 0 else ""}{d_net_tx:,.1f} KB/s vs. Baseline</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # 1. Simulated Telemetry Snapshot
            st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 1. Simulated Hardware Telemetry `[SIMULATED]`")
            render_metric_cards(sim_res.metrics, is_simulated=True)

            # 2. Machine Learning Evaluation
            st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 2. Machine Learning Pipeline Evaluation")
            render_health_and_risk(
                prediction=sim_res.prediction,
                is_model_trained=service.prediction_service.is_model_ready(),
                theme="dark",
            )

            # 3. Explainable Diagnostic Report
            st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
            st.markdown("#### 3. Explainable Diagnostic Recommendations")
            render_diagnostic_report(sim_diag, theme="dark")

    # -------------------------------------------------------------------------
    # Page: Real-Time Monitoring
    # -------------------------------------------------------------------------
    elif page == "⚡ Real-Time Monitoring":
        st.markdown(
            '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">'
            '<div>'
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="background:rgba(16, 185, 129, 0.16); color:#10B981; border:1px solid rgba(16, 185, 129, 0.4); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:0.8px;">LIVE MONITORING</span>'
            '<span style="font-size:12px; color:#94A3B8; text-transform:uppercase; font-weight:600; letter-spacing:0.5px;">Continuous Host Ingestion</span>'
            '</div>'
            '<h2 style="margin:4px 0 2px 0; font-size:22px; font-weight:700; color:#F8FAFC;">Live Operational Telemetry &amp; Worker Operations</h2>'
            '<p style="margin:0; font-size:13px; color:#94A3B8;">Real-time host sensor telemetry acquisition, background collector controls, on-demand instantaneous hardware probes, and streaming timeseries inspection.</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        col_worker, col_probe = st.columns([1.3, 1.0])

        with col_worker:
            is_running = service.is_background_monitoring_running()
            if is_running:
                st.markdown(
                    '<div class="aiops-metric-card" style="border-left: 3px solid #10B981; margin-bottom: 10px;">'
                    '<div style="display: flex; align-items: center; justify-content: space-between;">'
                    '<div>'
                    '<div style="font-size: 11px; font-weight: 700; color: #10B981; text-transform: uppercase; letter-spacing: 0.6px;">Collector Worker Status</div>'
                    '<div style="font-size: 15px; font-weight: 700; color: #F8FAFC; margin-top: 2px;">🟢 ACTIVE — Ingesting Background Telemetry</div>'
                    '</div>'
                    '<span style="font-size: 11px; color: #94A3B8; background: #111827; padding: 3px 8px; border-radius: 4px; border: 1px solid #293548;">Thread Safe</span>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if st.button("⏹️ Stop Collector Thread", key="btn_stop_worker", width="stretch"):
                    service.stop_background_monitoring()
                    st.rerun()
            else:
                st.markdown(
                    '<div class="aiops-metric-card" style="border-left: 3px solid #94A3B8; margin-bottom: 10px;">'
                    '<div style="display: flex; align-items: center; justify-content: space-between;">'
                    '<div>'
                    '<div style="font-size: 11px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.6px;">Collector Worker Status</div>'
                    '<div style="font-size: 15px; font-weight: 700; color: #F8FAFC; margin-top: 2px;">⚪ STOPPED — Idle / External Daemon Mode</div>'
                    '</div>'
                    '<span style="font-size: 11px; color: #94A3B8; background: #111827; padding: 3px 8px; border-radius: 4px; border: 1px solid #293548;">Standby</span>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                if st.button("▶️ Start Collector Thread", key="btn_start_worker", type="primary", width="stretch"):
                    service.start_background_monitoring()
                    st.rerun()

        with col_probe:
            st.markdown(
                '<div class="aiops-metric-card" style="margin-bottom: 10px;">'
                '<div style="font-size: 11px; font-weight: 700; color: #38BDF8; text-transform: uppercase; letter-spacing: 0.6px;">Instantaneous Telemetry Probe</div>'
                '<div style="font-size: 12px; color: #94A3B8; margin-top: 4px;">Harvest a fresh sensor snapshot across all subsystems and persist immediately to SQLite:</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("⚡ Trigger Snapshot Now", key="btn_trigger_snapshot", width="stretch"):
                with st.spinner("Harvesting live hardware telemetry..."):
                    rec, pred, err = service.capture_live_snapshot(persist=True)
                    if err:
                        st.error(f"Snapshot error: {err}")
                    else:
                        st.success("Telemetry sample captured and committed to SQLite!")
                        st.rerun()

        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        st.markdown("#### Live Telemetry Readings")
        render_metric_cards(latest_metric)

        # Subsystem Resource Breakdown Gauge
        fig_breakdown = build_resource_breakdown_bar(latest_metric, theme="dark")
        st.plotly_chart(fig_breakdown, width="stretch")

        if latest_pred:
            st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
            st.markdown("#### Real-Time Health & Anomaly Output")
            col_sc, col_an, col_rk, col_md = st.columns(4)
            with col_sc:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Composite Health Score</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F8FAFC; margin-top:4px;">{latest_pred.health_score:.1f} <span style="font-size:12px; color:#94A3B8;">/ 100</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_an:
                anom_color = "#EF4444" if latest_pred.is_anomaly else "#10B981"
                anom_status = "OUTLIER" if latest_pred.is_anomaly else "NOMINAL"
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Anomaly Probability</div>'
                    f'<div style="font-size:22px; font-weight:700; color:{anom_color}; margin-top:4px;">{latest_pred.anomaly_score:.4f} <span style="font-size:11px; padding:2px 6px; border-radius:3px; background:rgba(255,255,255,0.06);">{anom_status}</span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_rk:
                b = get_theme_risk_badge(latest_pred.risk_category)
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Evaluated Risk Tier</div>'
                    f'<div style="font-size:18px; font-weight:700; color:{b["color"]}; margin-top:4px;">{b["icon"]} {b["label"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_md:
                is_trained = service.prediction_service.is_model_ready()
                m_color = "#38BDF8" if is_trained else "#F59E0B"
                m_label = "Isolation Forest Active" if is_trained else "Heuristic Baseline"
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Inference Pipeline</div>'
                    f'<div style="font-size:15px; font-weight:700; color:{m_color}; margin-top:6px;">⚡ {m_label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Recent Telemetry Activity Stream (Last 30 Samples)
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        st.markdown("#### Live Telemetry Activity Stream")
        recent_metrics = service.get_historical_metrics(limit=30)
        if recent_metrics:
            fig_ts = build_multi_metric_timeseries(recent_metrics, theme="dark")
            st.plotly_chart(fig_ts, width="stretch")

            st.markdown("<div style='font-size:12px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.6px; margin: 12px 0 6px 0;'>Recent Telemetry Ingestion Log</div>", unsafe_allow_html=True)
            table_rows = []
            for rm in reversed(recent_metrics[-10:]):
                cpu_str = f"{rm.cpu_percent:.1f}%" if rm.cpu_percent is not None else "N/A"
                ram_str = f"{rm.memory_percent:.1f}%" if rm.memory_percent is not None else "N/A"
                disk_str = f"{rm.disk_percent:.1f}%" if rm.disk_percent is not None else "N/A"
                tx_kb = (rm.network_bytes_sent_per_sec / 1024) if rm.network_bytes_sent_per_sec is not None else 0.0
                rx_kb = (rm.network_bytes_recv_per_sec / 1024) if rm.network_bytes_recv_per_sec is not None else 0.0
                table_rows.append({
                    "Timestamp (UTC)": rm.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "CPU (%)": cpu_str,
                    "Memory (%)": ram_str,
                    "Disk (%)": disk_str,
                    "TX (KB/s)": f"{tx_kb:,.1f}",
                    "RX (KB/s)": f"{rx_kb:,.1f}",
                    "Dominant Process": f"{rm.top_process_name or 'N/A'} (PID: {rm.top_process_pid or '—'})",
                })
            st.dataframe(table_rows, width="stretch", hide_index=True)

    # -------------------------------------------------------------------------
    # Page 4: Historical Telemetry
    # -------------------------------------------------------------------------
    elif page == "📈 Historical Telemetry":
        st.markdown(
            '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">'
            '<div>'
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="background:rgba(56, 189, 248, 0.16); color:#38BDF8; border:1px solid rgba(56, 189, 248, 0.4); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:0.8px;">HISTORICAL OBSERVABILITY</span>'
            '<span style="font-size:12px; color:#94A3B8; text-transform:uppercase; font-weight:600; letter-spacing:0.5px;">Telemetry Archive &amp; Trend Analysis</span>'
            '</div>'
            '<h2 style="margin:4px 0 2px 0; font-size:22px; font-weight:700; color:#F8FAFC;">Historical Telemetry &amp; Multi-Series Trends</h2>'
            '<p style="margin:0; font-size:13px; color:#94A3B8;">Long-horizon multi-subsystem metric inspection, capacity headroom tracking, hardware saturation correlation, and historical CSV telemetry export.</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        col_filter1, col_filter2 = st.columns([1, 2])

        with col_filter1:
            time_range = st.selectbox(
                "Select Time Horizon",
                options=[
                    "Last 15 Minutes",
                    "Last 1 Hour",
                    "Last 6 Hours",
                    "Last 24 Hours",
                    "All Persisted Records",
                ],
                index=1,
            )

        with col_filter2:
            selected_metrics = st.multiselect(
                "Select Telemetry Series to Plot",
                options=[
                    "CPU Utilization (%)",
                    "RAM Utilization (%)",
                    "Disk Utilization (%)",
                    "Network TX (KB/s)",
                    "Network RX (KB/s)",
                    "Active Processes",
                ],
                default=["CPU Utilization (%)", "RAM Utilization (%)", "Disk Utilization (%)"],
            )

        now = datetime.now(timezone.utc)
        start_dt: Optional[datetime] = None
        if time_range == "Last 15 Minutes":
            start_dt = now - timedelta(minutes=15)
        elif time_range == "Last 1 Hour":
            start_dt = now - timedelta(hours=1)
        elif time_range == "Last 6 Hours":
            start_dt = now - timedelta(hours=6)
        elif time_range == "Last 24 Hours":
            start_dt = now - timedelta(hours=24)

        hist_records = service.get_historical_metrics(
            start_time=start_dt,
            end_time=now if start_dt else None,
            limit=settings.dashboard_historical_limit,
        )

        if hist_records:
            # Summary Statistics KPI Cards
            cpus = [r.cpu_percent for r in hist_records if r.cpu_percent is not None]
            rams = [r.memory_percent for r in hist_records if r.memory_percent is not None]
            disks = [r.disk_percent for r in hist_records if r.disk_percent is not None]

            avg_cpu = (sum(cpus) / len(cpus)) if cpus else 0.0
            peak_cpu = max(cpus) if cpus else 0.0
            avg_ram = (sum(rams) / len(rams)) if rams else 0.0
            peak_ram = max(rams) if rams else 0.0
            avg_disk = (sum(disks) / len(disks)) if disks else 0.0

            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            with col_s1:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Archived Records</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F8FAFC; margin-top:2px;">{len(hist_records):,} <span style="font-size:12px; color:#94A3B8;">samples</span></div>'
                    f'<div style="font-size:11px; color:#38BDF8; margin-top:2px;">Horizon: {time_range}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_s2:
                cpu_accent = "#EF4444" if peak_cpu >= 90.0 else ("#F59E0B" if peak_cpu >= 80.0 else "#10B981")
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">CPU Load Profile</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F8FAFC; margin-top:2px;">{avg_cpu:.1f}% <span style="font-size:12px; color:#94A3B8;">avg</span></div>'
                    f'<div style="font-size:11px; color:{cpu_accent}; margin-top:2px;">Peak: {peak_cpu:.1f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_s3:
                ram_accent = "#EF4444" if peak_ram >= 90.0 else ("#F59E0B" if peak_ram >= 80.0 else "#10B981")
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Memory Utilization</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F8FAFC; margin-top:2px;">{avg_ram:.1f}% <span style="font-size:12px; color:#94A3B8;">avg</span></div>'
                    f'<div style="font-size:11px; color:{ram_accent}; margin-top:2px;">Peak: {peak_ram:.1f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_s4:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Storage Utilization</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F8FAFC; margin-top:2px;">{avg_disk:.1f}% <span style="font-size:12px; color:#94A3B8;">avg</span></div>'
                    f'<div style="font-size:11px; color:#10B981; margin-top:2px;">Filesystem Stable</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
            col_c1, col_c2 = st.columns([3, 1])
            with col_c1:
                st.caption(f"Displaying **{len(hist_records)}** historical records from SQLite across the selected time horizon.")
            with col_c2:
                csv_metrics = service.export_metrics_csv(
                    start_time=start_dt,
                    end_time=now if start_dt else None,
                    limit=settings.dashboard_historical_limit,
                )
                st.download_button(
                    label="⬇️ Export Telemetry CSV",
                    data=csv_metrics,
                    file_name=f"telemetry_metrics_{now.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width="stretch",
                )

            fig_ts = build_multi_metric_timeseries(hist_records, selected_metrics=selected_metrics, theme="dark")
            st.plotly_chart(fig_ts, width="stretch")

            with st.expander("📄 View Historical Records Table", expanded=False):
                df_hist = pd.DataFrame(
                    [
                        {
                            "Timestamp (UTC)": format_timestamp(r.timestamp),
                            "CPU (%)": f"{r.cpu_percent:.1f}%" if r.cpu_percent is not None else "N/A",
                            "RAM (%)": f"{r.memory_percent:.1f}%" if r.memory_percent is not None else "N/A",
                            "Disk (%)": f"{r.disk_percent:.1f}%" if r.disk_percent is not None else "N/A",
                            "TX (KB/s)": f"{((r.network_bytes_sent_per_sec or 0.0) / 1024.0):,.1f}",
                            "RX (KB/s)": f"{((r.network_bytes_recv_per_sec or 0.0) / 1024.0):,.1f}",
                            "Processes": r.process_count if r.process_count is not None else "—",
                            "Top Process": f"{r.top_process_name or 'N/A'} (PID: {r.top_process_pid or '—'})",
                        }
                        for r in hist_records
                    ]
                )
                st.dataframe(df_hist, width="stretch", hide_index=True)
        else:
            st.markdown(
                f"""<div class="aiops-empty-state">
                    <div style="font-size:28px;">📈</div>
                    <div class="title">No Historical Telemetry Recorded</div>
                    <div class="desc">No sensor telemetry was found in SQLite within the selected time window ({time_range}). Capture a live snapshot or start the background collector worker to begin logging historical telemetry.</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # Page 5: Anomaly Audit Log
    # -------------------------------------------------------------------------
    elif page == "🔍 Anomaly Audit Log":
        st.markdown(
            '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">'
            '<div>'
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="background:rgba(239, 68, 68, 0.16); color:#EF4444; border:1px solid rgba(239, 68, 68, 0.4); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:0.8px;">AUDIT INTELLIGENCE</span>'
            '<span style="font-size:12px; color:#94A3B8; text-transform:uppercase; font-weight:600; letter-spacing:0.5px;">Isolation Forest Anomaly Records</span>'
            '</div>'
            '<h2 style="margin:4px 0 2px 0; font-size:22px; font-weight:700; color:#F8FAFC;">Historical Anomaly Audit &amp; Event Review</h2>'
            '<p style="margin:0; font-size:13px; color:#94A3B8;">Correlates historical 39-feature vectors with Isolation Forest anomaly evaluations, risk tiers, and hardware saturation levels.</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        col_cfg1, col_cfg2 = st.columns([1.2, 1.0])
        with col_cfg1:
            limit = st.slider("Audit Depth (Max Records)", min_value=10, max_value=500, value=100, step=10)
        with col_cfg2:
            st.markdown(
                f'<div style="font-size:12px; color:#94A3B8; margin-top:8px;">'
                f'Active Inference Engine: <code style="color:#38BDF8;">{service.prediction_service.model_name}</code><br>'
                f'Decision Boundary: <code style="color:#EF4444;">Anomaly Score &gt; 0.50</code>'
                f'</div>',
                unsafe_allow_html=True,
            )

        anomalies = service.get_historical_anomalies(limit=limit)

        if anomalies:
            # Audit Summary KPI Cards
            total_eval = len(anomalies)
            outliers = sum(1 for a in anomalies if a.get("is_anomaly"))
            outlier_rate = (outliers / total_eval * 100.0) if total_eval > 0 else 0.0
            crit_count = sum(1 for a in anomalies if a.get("risk_category") == "Critical")
            high_count = sum(1 for a in anomalies if a.get("risk_category") == "High")
            mod_count = sum(1 for a in anomalies if a.get("risk_category") == "Moderate")

            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Evaluated Vectors</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F8FAFC; margin-top:2px;">{total_eval:,} <span style="font-size:12px; color:#94A3B8;">samples</span></div>'
                    f'<div style="font-size:11px; color:#38BDF8; margin-top:2px;">Feature dimension: 39-D</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_a2:
                outlier_color = "#EF4444" if outliers > 0 else "#10B981"
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Flagged Outliers</div>'
                    f'<div style="font-size:22px; font-weight:700; color:{outlier_color}; margin-top:2px;">{outliers:,} <span style="font-size:12px; color:#94A3B8;">({outlier_rate:.1f}%)</span></div>'
                    f'<div style="font-size:11px; color:#94A3B8; margin-top:2px;">Score &gt; 0.50 Threshold</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_a3:
                crit_color = "#EF4444" if crit_count > 0 else "#94A3B8"
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Critical Incidents</div>'
                    f'<div style="font-size:22px; font-weight:700; color:{crit_color}; margin-top:2px;">{crit_count:,} <span style="font-size:12px; color:#94A3B8;">events</span></div>'
                    f'<div style="font-size:11px; color:#94A3B8; margin-top:2px;">Severe Saturation/Risk</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_a4:
                st.markdown(
                    f'<div class="aiops-metric-card">'
                    f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">High / Moderate</div>'
                    f'<div style="font-size:22px; font-weight:700; color:#F59E0B; margin-top:2px;">{high_count + mod_count:,} <span style="font-size:12px; color:#94A3B8;">events</span></div>'
                    f'<div style="font-size:11px; color:#94A3B8; margin-top:2px;">Elevated Behavioral Shift</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
            fig_scatter = build_anomaly_scatter_chart(anomalies, theme="dark")
            st.plotly_chart(fig_scatter, width="stretch")

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_anom = st.checkbox("Show Flagged Anomalies Only (Score > 0.50)", value=False)
            with col_f2:
                filter_risk = st.multiselect(
                    "Filter Risk Tiers",
                    options=["Critical", "High", "Moderate", "Low", "Normal"],
                    default=["Critical", "High", "Moderate", "Low", "Normal"],
                )

            filtered = [
                a for a in anomalies
                if (not filter_anom or a["is_anomaly"])
                and (a["risk_category"] in filter_risk)
            ]

            col_m1, col_m2 = st.columns([3, 1])
            with col_m1:
                st.caption(f"Found **{len(filtered)}** matching evaluation records in the audit range.")
            with col_m2:
                csv_anom = service.export_anomalies_csv(limit=limit, filter_anomalies_only=filter_anom)
                st.download_button(
                    label="⬇️ Export Audit Log CSV",
                    data=csv_anom,
                    file_name=f"anomaly_audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    width="stretch",
                )

            df_anom = pd.DataFrame(
                [
                    {
                        "Timestamp (UTC)": format_timestamp(a["timestamp"]),
                        "Anomaly Score": f"{a['anomaly_score']:.4f}",
                        "Outlier Flag": "🔴 YES" if a["is_anomaly"] else "🟢 NO",
                        "Risk Tier": a["risk_category"],
                        "Health Score": f"{a['health_score']:.1f}/100" if a["health_score"] is not None else "N/A",
                        "CPU (%)": f"{a.get('cpu_percent', 0.0):.1f}%",
                        "RAM (%)": f"{a.get('memory_percent', 0.0):.1f}%",
                        "Disk (%)": f"{a.get('disk_percent', 0.0):.1f}%",
                        "Evaluator": a.get("model_name", "N/A"),
                    }
                    for a in filtered
                ]
            )
            st.dataframe(df_anom, width="stretch", hide_index=True)

            # Investigation Inspector for a Selected Anomaly
            if filtered:
                st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
                st.markdown("#### 🔬 Detailed Event Diagnostics &amp; Feature Inspector")
                st.caption("Select any recorded evaluation from the audit log to inspect its underlying telemetry evidence and diagnostic recommendations.")

                event_options = [
                    f"#{filtered[i]['feature_id']} — {format_timestamp(filtered[i]['timestamp'])} — Score: {filtered[i]['anomaly_score']:.4f} ({filtered[i]['risk_category']})"
                    for i in range(len(filtered))
                ]
                sel_idx = st.selectbox("Select Anomaly Evaluation Event to Inspect", options=range(len(filtered)), format_func=lambda i: event_options[i])
                sel_anom = filtered[sel_idx]

                # Generate on-demand diagnostic report for selected event
                diag_for_event = service.diagnostic_engine.generate_report(
                    prediction=None,
                    metrics={
                        "cpu_percent": sel_anom.get("cpu_percent"),
                        "memory_percent": sel_anom.get("memory_percent"),
                        "disk_percent": sel_anom.get("disk_percent"),
                        "net_tx_kbps": (sel_anom.get("network_kbps", 0.0) / 2.0),
                        "net_rx_kbps": (sel_anom.get("network_kbps", 0.0) / 2.0),
                    },
                    timestamp=sel_anom["timestamp"],
                )
                render_diagnostic_report(diag_for_event, theme="dark")
        else:
            st.markdown(
                f"""<div class="aiops-empty-state">
                    <div style="font-size:28px;">🔍</div>
                    <div class="title">No Anomaly History Available</div>
                    <div class="desc">No historical feature vectors are available in SQLite to evaluate. Capture a snapshot or run the background collector worker to begin logging audit evaluations.</div>
                </div>""",
                unsafe_allow_html=True,
            )

    # -------------------------------------------------------------------------
    # Page 6: Database & Operational Status
    # -------------------------------------------------------------------------
    elif page in ("🗄️ Database & Operational Status", "🗄️ Database Inspection"):
        st.markdown(
            '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">'
            '<div>'
            '<div style="display:flex; align-items:center; gap:8px;">'
            '<span style="background:rgba(56, 189, 248, 0.16); color:#38BDF8; border:1px solid rgba(56, 189, 248, 0.4); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:800; letter-spacing:0.8px;">PLATFORM HEALTH</span>'
            '<span style="font-size:12px; color:#94A3B8; text-transform:uppercase; font-weight:600; letter-spacing:0.5px;">Persistence &amp; Subsystem Operations</span>'
            '</div>'
            '<h2 style="margin:4px 0 2px 0; font-size:22px; font-weight:700; color:#F8FAFC;">Subsystem Operational Health Status &amp; SQLite Inspector</h2>'
            '<p style="margin:0; font-size:13px; color:#94A3B8;">Live operational heartbeat checks, SQLite WAL storage metrics, table row counts, and schema explorer.</p>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        op_status = service.get_operational_status()

        # Operational Status Banner
        overall = op_status["overall_status"]
        if overall == "HEALTHY":
            status_color = "#10B981"
            status_icon = "🟢"
        elif overall == "DEGRADED":
            status_color = "#F59E0B"
            status_icon = "🟡"
        else:
            status_color = "#EF4444"
            status_icon = "🔴"

        banner_html = (
            f'<div class="aiops-metric-card" style="border-left:4px solid {status_color}; margin-bottom:18px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">'
            f'<div>'
            f'<div style="font-size:11px; font-weight:700; color:{status_color}; text-transform:uppercase; letter-spacing:0.8px;">System Operational Status &bull; {overall}</div>'
            f'<div style="font-size:18px; font-weight:700; color:#F8FAFC; margin-top:2px;">{status_icon} Platform Status: {overall}</div>'
            f'<div style="font-size:13px; color:#94A3B8; margin-top:3px;">{op_status["headline"]}</div>'
            f'</div>'
            f'<div style="font-size:12px; color:#94A3B8; background:#111827; padding:6px 12px; border-radius:4px; border:1px solid #293548;">'
            f'Evaluation: {format_timestamp(datetime.now(timezone.utc))}'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(banner_html, unsafe_allow_html=True)

        # Subsystems Status Cards
        st.markdown("#### 🏥 Subsystem Operational Health Checks")
        sc1, sc2, sc3, sc4 = st.columns(4)

        with sc1:
            db_sub = op_status["subsystems"]["database"]
            db_icon = "🟢" if db_sub["status"] == "OPERATIONAL" else "🔴"
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">SQLite Persistence</div>'
                f'<div style="font-size:18px; font-weight:700; color:#F8FAFC; margin-top:2px;">{db_icon} {db_sub["status"]}</div>'
                f'<div style="font-size:11px; color:#10B981; margin-top:2px;">Integrity: {db_sub["integrity"]}</div>'
                f'<div style="font-size:11px; color:#94A3B8; margin-top:4px;">Rows: {db_sub["telemetry_rows"]:,}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with sc2:
            ml_sub = op_status["subsystems"]["ml_engine"]
            ml_icon = "🟢" if ml_sub["status"] == "OPERATIONAL" else "🟡"
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">ML Model Engine</div>'
                f'<div style="font-size:18px; font-weight:700; color:#F8FAFC; margin-top:2px;">{ml_icon} {ml_sub["status"]}</div>'
                f'<div style="font-size:11px; color:#38BDF8; margin-top:2px;">{ml_sub["model_name"]}</div>'
                f'<div style="font-size:11px; color:#94A3B8; margin-top:4px;">{ml_sub["mode"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with sc3:
            col_sub = op_status["subsystems"]["collector"]
            col_icon = "🟢" if col_sub["status"] == "OPERATIONAL" else "🔴"
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Hardware Collectors</div>'
                f'<div style="font-size:18px; font-weight:700; color:#F8FAFC; margin-top:2px;">{col_icon} {col_sub["status"]}</div>'
                f'<div style="font-size:11px; color:#10B981; margin-top:2px;">{len(col_sub["domains"])} Monitored Domains</div>'
                f'<div style="font-size:11px; color:#94A3B8; margin-top:4px;">{", ".join(col_sub["domains"][:3])}...</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with sc4:
            fresh_sub = op_status["subsystems"]["telemetry_freshness"]
            f_icon = "🟢" if fresh_sub["status"] == "FRESH" else ("🟡" if fresh_sub["status"] == "WARM" else "⚪")
            delta_val = f"{fresh_sub['seconds_since_last_sample']}s ago" if fresh_sub['seconds_since_last_sample'] is not None else "No telemetry"
            worker_stat = op_status['subsystems']['background_worker']['status']
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Ingestion Freshness</div>'
                f'<div style="font-size:18px; font-weight:700; color:#F8FAFC; margin-top:2px;">{f_icon} {fresh_sub["status"]}</div>'
                f'<div style="font-size:11px; color:#38BDF8; margin-top:2px;">{delta_val}</div>'
                f'<div style="font-size:11px; color:#94A3B8; margin-top:4px;">Worker: {worker_stat}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        st.markdown("#### 🗄️ SQLite Storage Metrics &amp; Table Capacities")

        db_summary = service.get_database_summary()

        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Database File</div>'
                f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{"Active" if db_summary["database_exists"] else "Missing"}</div>'
                f'<div style="font-size:11px; color:#38BDF8; margin-top:2px;">Size: {format_bytes(db_summary["file_size_bytes"])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_d2:
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Telemetry Rows</div>'
                f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{db_summary["counts"]["system_metrics"]:,}</div>'
                f'<div style="font-size:11px; color:#10B981; margin-top:2px;">table: system_metrics</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_d3:
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Feature Vectors</div>'
                f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{db_summary["counts"]["feature_vectors"]:,}</div>'
                f'<div style="font-size:11px; color:#10B981; margin-top:2px;">table: feature_vectors</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_d4:
            st.markdown(
                f'<div class="aiops-metric-card">'
                f'<div style="font-size:11px; font-weight:700; color:#94A3B8; text-transform:uppercase;">Validation Logs</div>'
                f'<div style="font-size:20px; font-weight:700; color:#F8FAFC; margin-top:2px;">{db_summary["counts"]["validation_logs"]:,}</div>'
                f'<div style="font-size:11px; color:#10B981; margin-top:2px;">table: validation_logs</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Inspect actual PRAGMAs from SQLite
        journal_mode = "WAL"
        foreign_keys = "ON"
        try:
            with get_connection(service.persistence.db_path, timeout=3.0) as conn:
                r_jm = conn.execute("PRAGMA journal_mode;").fetchone()
                if r_jm:
                    journal_mode = str(r_jm[0]).upper()
                r_fk = conn.execute("PRAGMA foreign_keys;").fetchone()
                if r_fk:
                    foreign_keys = "ON" if r_fk[0] == 1 else "OFF"
        except Exception:
            pass

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"**Database Location:** `{db_summary['database_path']}`")
            st.markdown(f"**Earliest Ingestion:** {format_timestamp(db_summary['earliest_timestamp'])}")
            st.markdown(f"**Latest Ingestion:** {format_timestamp(db_summary['latest_timestamp'])}")
        with col_meta2:
            st.markdown(f"**Journal Mode:** `{journal_mode}` (`PRAGMA journal_mode = {journal_mode};`)")
            st.markdown(f"**Foreign Keys:** `{foreign_keys}` (`PRAGMA foreign_keys = {foreign_keys};`)")
            ret_days = db_summary.get("retention_days")
            st.markdown(f"**Retention Policy:** {f'{ret_days} days' if ret_days else 'Indefinite'}")

        st.markdown("<div style='margin-top:24px;'></div>", unsafe_allow_html=True)
        col_exp_title, col_exp_btn = st.columns([2, 1])
        with col_exp_title:
            st.markdown("#### 🔍 Table Data &amp; Schema Explorer")
        table_choice = st.selectbox("Select Table to Inspect", ["system_metrics", "feature_vectors", "validation_logs"])
        table_limit = st.slider("Rows to Display", min_value=5, max_value=100, value=15, step=5)

        with col_exp_btn:
            if table_choice == "feature_vectors":
                csv_tbl = service.export_features_csv(limit=table_limit)
                file_name = f"feature_vectors_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            else:
                csv_tbl = service.export_metrics_csv(limit=table_limit)
                file_name = f"system_metrics_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
            st.download_button(
                label=f"⬇️ Export {table_choice} CSV",
                data=csv_tbl,
                file_name=file_name,
                mime="text/csv",
                width="stretch",
            )

        if table_choice == "system_metrics":
            records = service.get_historical_metrics(limit=table_limit)
            if records:
                df_sys = pd.DataFrame([
                    {
                        "ID": r.id,
                        "Timestamp (UTC)": format_timestamp(r.timestamp),
                        "CPU (%)": f"{r.cpu_percent:.1f}%" if r.cpu_percent is not None else "N/A",
                        "RAM (%)": f"{r.memory_percent:.1f}%" if r.memory_percent is not None else "N/A",
                        "Disk (%)": f"{r.disk_percent:.1f}%" if r.disk_percent is not None else "N/A",
                        "TX (KB/s)": f"{((r.network_bytes_sent_per_sec or 0.0) / 1024.0):,.1f}",
                        "RX (KB/s)": f"{((r.network_bytes_recv_per_sec or 0.0) / 1024.0):,.1f}",
                        "Processes": r.process_count or "—",
                        "Top Process": f"{r.top_process_name or 'N/A'} (PID: {r.top_process_pid or '—'})",
                    }
                    for r in reversed(records)
                ])
                st.dataframe(df_sys, width="stretch", hide_index=True)
            else:
                st.info("No records found in system_metrics.")
        elif table_choice == "feature_vectors":
            features = service.get_historical_features(limit=table_limit)
            if features:
                df_feat = pd.DataFrame([
                    {
                        "Feature ID": f.id,
                        "Metric ID": f.metric_id or "—",
                        "Timestamp (UTC)": format_timestamp(f.timestamp),
                        "CPU Utilization": f"{f.features.get('cpu_utilization_percent', 0.0):.1f}%",
                        "RAM Utilization": f"{f.features.get('memory_utilization_percent', 0.0):.1f}%",
                        "Disk Utilization": f"{f.features.get('disk_utilization_percent', 0.0):.1f}%",
                        "Load 1m": f"{f.features.get('cpu_load_1m', 0.0):.2f}",
                        "Features Count": len(f.features),
                    }
                    for f in reversed(features)
                ])
                st.dataframe(df_feat, width="stretch", hide_index=True)
            else:
                st.info("No records found in feature_vectors.")
        elif table_choice == "validation_logs":
            logs = service.get_recent_validation_logs(limit=table_limit)
            if logs:
                df_logs = pd.DataFrame([
                    {
                        "ID": l.id,
                        "Timestamp (UTC)": format_timestamp(l.timestamp),
                        "Component": l.component,
                        "Status": l.status,
                        "Issue Count": l.issue_count,
                        "Details": l.details,
                    }
                    for l in reversed(logs)
                ])
                st.dataframe(df_logs, width="stretch", hide_index=True)
            else:
                st.info("No records found in validation_logs.")

    # -------------------------------------------------------------------------
    # Auto-Refresh Handler
    # -------------------------------------------------------------------------
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
