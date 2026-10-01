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
)
from app.dashboard.components.health_card import render_health_and_risk
from app.dashboard.components.metrics_cards import render_metric_cards
from app.dashboard.components.status_header import render_status_header
from app.dashboard.services.dashboard_service import DashboardService
from app.dashboard.utils.formatting import format_bytes, format_percent, format_timestamp, get_risk_badge


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
    settings: Settings = service.settings

    # -------------------------------------------------------------------------
    # Sidebar Navigation & Operational Controls
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### 🖥️ Navigation")
        page = st.radio(
            label="Select View",
            options=[
                "📊 System Overview",
                "🛡️ Health & Risk Analysis",
                "⚡ Real-Time Monitoring",
                "📈 Historical Telemetry",
                "🔍 Anomaly Audit Log",
                "🗄️ Database Inspection",
            ],
            index=0,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### ⚙️ Live Controls")

        # Snapshot button
        if st.button("📸 Capture Live Snapshot", use_container_width=True, type="primary"):
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
            if st.button("⏹️ Stop Background Worker", use_container_width=True):
                service.stop_background_monitoring()
                st.info("Stopped background monitoring thread.")
                st.rerun()
        else:
            if st.button("▶️ Start Background Worker", use_container_width=True):
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

        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()

        st.markdown("---")
        # System & Model metadata in sidebar
        is_model_trained = service.prediction_service.is_model_ready()
        model_name = service.prediction_service.model_name
        summary = service.get_database_summary()

        st.markdown("### ℹ️ Engine Info")
        st.caption(f"**ML Engine:** {model_name}")
        st.caption(f"**ML Status:** {'🟢 Trained Artifact' if is_model_trained else '⚠️ Heuristic Baseline'}")
        st.caption(f"**Worker:** {'🟢 Active' if is_bg_running else '⚪ Idle'}")
        st.caption(f"**SQLite Samples:** {summary['counts']['system_metrics']:,}")

    # -------------------------------------------------------------------------
    # Shared Data Loading
    # -------------------------------------------------------------------------
    latest_metric = service.get_latest_metrics()
    latest_pred = service.get_latest_prediction()
    last_ts = latest_metric.timestamp if latest_metric else None

    # Render top status header on all pages
    render_status_header(
        last_updated=last_ts,
        is_monitoring=service.is_background_monitoring_running(),
        model_name=service.prediction_service.model_name,
        is_model_trained=service.prediction_service.is_model_ready(),
        db_record_count=summary["counts"]["system_metrics"],
    )

    # -------------------------------------------------------------------------
    # Page 1: System Overview
    # -------------------------------------------------------------------------
    if page == "📊 System Overview":
        st.subheader("Current Hardware & OS Telemetry Snapshot")
        render_metric_cards(latest_metric)

        st.markdown("<br>", unsafe_allow_html=True)
        col_res, col_quick_health = st.columns([1.6, 1.4])

        with col_res:
            fig_bar = build_resource_breakdown_bar(latest_metric)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_quick_health:
            st.markdown("#### Operational Health Status")
            if latest_pred:
                badge = get_risk_badge(latest_pred.risk_category)
                health_val = f"{latest_pred.health_score:.1f}/100" if latest_pred.health_score is not None else "N/A"
                st.markdown(
                    f"""
                    <div style='background-color:#F8FAFC; border:1px solid #E2E8F0; padding:18px; border-radius:8px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <span style='font-size:14px; font-weight:600; color:#475569;'>Composite Health Score:</span>
                            <span style='font-size:24px; font-weight:800; color:{badge["color"]};'>{health_val}</span>
                        </div>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:12px;'>
                            <span style='font-size:14px; font-weight:600; color:#475569;'>Operational Risk Tier:</span>
                            <span style='font-size:16px; font-weight:700; color:{badge["color"]};'>{badge["icon"]} {badge["label"]}</span>
                        </div>
                        <div style='display:flex; justify-content:space-between; align-items:center; margin-top:12px;'>
                            <span style='font-size:14px; font-weight:600; color:#475569;'>Anomaly Probability:</span>
                            <span style='font-size:16px; font-weight:700; color:#334155;'>{latest_pred.anomaly_score:.4f}</span>
                        </div>
                        <hr style='margin:12px 0; border-color:#E2E8F0;'>
                        <p style='font-size:12px; color:#64748B; margin:0;'>
                            {badge["description"]}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("No health predictions evaluated yet. Click 'Capture Live Snapshot' in the sidebar.")

        # Recent 5 telemetry samples table
        st.markdown("#### Recent Telemetry Ingestion Log")
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
                        "Processes": s.process_count,
                        "Top Process": f"{s.top_process_name} ({s.top_process_cpu_percent or 0.0:.1f}%)" if s.top_process_name else "N/A",
                    }
                    for s in reversed(recent_samples)
                ]
            )
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
        else:
            st.info("No recent samples available in database.")

    # -------------------------------------------------------------------------
    # Page 2: Health & Risk Analysis
    # -------------------------------------------------------------------------
    elif page == "🛡️ Health & Risk Analysis":
        st.subheader("Machine Learning Anomaly Detection & Failure Risk Tiers")
        render_health_and_risk(
            prediction=latest_pred,
            is_model_trained=service.prediction_service.is_model_ready(),
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Risk Categorization Reference Matrix")

        tier_cols = st.columns(5)
        tiers = [
            ("Normal", "< 0.35", "80 - 100", "#10B981", "Nominal telemetry pattern matching training baseline."),
            ("Low", "0.35 - 0.55", "65 - 79", "#3B82F6", "Mild metric variance; well within normal parameters."),
            ("Moderate", "0.55 - 0.75", "45 - 64", "#F59E0B", "Noticeable divergence from normal baseline cluster."),
            ("High", "0.75 - 0.90", "25 - 44", "#F97316", "Significant behavioral outlier; review workload/processes."),
            ("Critical", ">= 0.90", "0 - 24", "#EF4444", "Severe anomaly or hardware saturation >=95%."),
        ]

        active_cat = latest_pred.risk_category.value if latest_pred else ""

        for idx, (name, thresh, health, col, desc) in enumerate(tiers):
            with tier_cols[idx]:
                is_active = active_cat == name
                border_style = f"3px solid {col}" if is_active else "1px solid #E2E8F0"
                bg_style = "rgba(16, 185, 129, 0.08)" if is_active else "#FFFFFF"
                active_badge = f"<span style='background:{col}; color:#FFF; font-size:10px; padding:2px 6px; border-radius:4px; font-weight:700;'>CURRENT</span>" if is_active else ""

                st.markdown(
                    f"""
                    <div style='border:{border_style}; background-color:{bg_style}; padding:12px; border-radius:8px; height:180px;'>
                        <div style='display:flex; justify-content:space-between; align-items:center;'>
                            <b style='color:{col}; font-size:15px;'>{name}</b>
                            {active_badge}
                        </div>
                        <div style='font-size:12px; color:#475569; margin-top:8px;'><b>Anomaly:</b> {thresh}</div>
                        <div style='font-size:12px; color:#475569;'><b>Health:</b> {health}</div>
                        <p style='font-size:11px; color:#64748B; margin-top:8px; line-height:1.3;'>{desc}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # -------------------------------------------------------------------------
    # Page 3: Real-Time Monitoring
    # -------------------------------------------------------------------------
    elif page == "⚡ Real-Time Monitoring":
        st.subheader("Live Operational Monitoring")

        st.markdown(
            """
            This view interfaces directly with the host telemetry collection engine.
            You can trigger individual on-demand snapshots, run the in-dashboard background worker,
            or run `python run.py` in an external terminal for high-frequency daemon collection.
            """
        )

        col_ctrl1, col_ctrl2 = st.columns(2)
        with col_ctrl1:
            st.markdown("#### Worker Control")
            if service.is_background_monitoring_running():
                st.success("🟢 Background collector worker is currently ACTIVE.")
                if st.button("Stop Collector Thread"):
                    service.stop_background_monitoring()
                    st.rerun()
            else:
                st.warning("⚪ Background collector worker is currently STOPPED.")
                if st.button("Start Collector Thread"):
                    service.start_background_monitoring()
                    st.rerun()

        with col_ctrl2:
            st.markdown("#### Single Snapshot")
            st.write("Execute a single-pass hardware telemetry probe and persist to SQLite:")
            if st.button("Trigger Snapshot Now"):
                with st.spinner("Harvesting metrics..."):
                    rec, pred, err = service.capture_live_snapshot(persist=True)
                    if err:
                        st.error(f"Snapshot error: {err}")
                    else:
                        st.success("Sample captured!")
                        st.rerun()

        st.markdown("---")
        st.markdown("#### Live Telemetry Readings")
        render_metric_cards(latest_metric)

        if latest_pred:
            st.markdown("#### Real-Time Health & Anomaly Output")
            col_sc, col_an, col_rk = st.columns(3)
            with col_sc:
                st.metric("Health Score", f"{latest_pred.health_score:.1f} / 100")
            with col_an:
                st.metric("Anomaly Probability", f"{latest_pred.anomaly_score:.4f}", delta="Outlier" if latest_pred.is_anomaly else "Nominal", delta_color="inverse" if latest_pred.is_anomaly else "normal")
            with col_rk:
                b = get_risk_badge(latest_pred.risk_category)
                st.metric("Risk Category", f"{b['icon']} {b['label']}")

    # -------------------------------------------------------------------------
    # Page 4: Historical Telemetry
    # -------------------------------------------------------------------------
    elif page == "📈 Historical Telemetry":
        st.subheader("Interactive Historical Telemetry Trends")

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

        st.caption(f"Displaying **{len(hist_records)}** historical records from SQLite.")

        fig_ts = build_multi_metric_timeseries(hist_records, selected_metrics=selected_metrics)
        st.plotly_chart(fig_ts, use_container_width=True)

        with st.expander("📄 View Historical Records Table", expanded=False):
            if hist_records:
                df_hist = pd.DataFrame(
                    [
                        {
                            "Timestamp (UTC)": format_timestamp(r.timestamp),
                            "CPU (%)": r.cpu_percent,
                            "RAM (%)": r.memory_percent,
                            "Disk (%)": r.disk_percent,
                            "TX (KB/s)": (r.network_bytes_sent_per_sec or 0.0) / 1024.0,
                            "RX (KB/s)": (r.network_bytes_recv_per_sec or 0.0) / 1024.0,
                            "Processes": r.process_count,
                            "Top Process": r.top_process_name,
                        }
                        for r in hist_records
                    ]
                )
                st.dataframe(df_hist, use_container_width=True)
            else:
                st.info("No records in the selected range.")

    # -------------------------------------------------------------------------
    # Page 5: Anomaly Audit Log
    # -------------------------------------------------------------------------
    elif page == "🔍 Anomaly Audit Log":
        st.subheader("Historical Anomaly Audit & Review")
        st.caption(
            "Correlates historical 39-feature vectors with Isolation Forest anomaly evaluations "
            "and hardware saturation levels."
        )

        limit = st.slider("Audit Depth (Max Records)", min_value=10, max_value=500, value=100, step=10)
        anomalies = service.get_historical_anomalies(limit=limit)

        if anomalies:
            fig_scatter = build_anomaly_scatter_chart(anomalies)
            st.plotly_chart(fig_scatter, use_container_width=True)

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

            st.markdown(f"Found **{len(filtered)}** matching evaluation records.")

            df_anom = pd.DataFrame(
                [
                    {
                        "Timestamp (UTC)": format_timestamp(a["timestamp"]),
                        "Anomaly Score": f"{a['anomaly_score']:.4f}",
                        "Outlier Flag": "🔴 YES" if a["is_anomaly"] else "🟢 NO",
                        "Risk Tier": a["risk_category"],
                        "Health Score": f"{a['health_score']:.1f}/100" if a["health_score"] is not None else "N/A",
                        "CPU %": f"{a.get('cpu_percent', 0.0):.1f}%",
                        "RAM %": f"{a.get('memory_percent', 0.0):.1f}%",
                        "Disk %": f"{a.get('disk_percent', 0.0):.1f}%",
                        "Evaluator": a.get("model_name", "N/A"),
                    }
                    for a in filtered
                ]
            )
            st.dataframe(df_anom, use_container_width=True, hide_index=True)
        else:
            st.info("No historical feature vectors available to evaluate.")

    # -------------------------------------------------------------------------
    # Page 6: Database Inspection
    # -------------------------------------------------------------------------
    elif page == "🗄️ Database Inspection":
        st.subheader("SQLite Persistence Engine & Schema Inspector")

        db_summary = service.get_database_summary()

        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        with col_d1:
            st.metric("Database File", "Exists" if db_summary["database_exists"] else "Missing", delta=format_bytes(db_summary["file_size_bytes"]))
        with col_d2:
            st.metric("Telemetry Rows", f"{db_summary['counts']['system_metrics']:,}")
        with col_d3:
            st.metric("Feature Vectors", f"{db_summary['counts']['feature_vectors']:,}")
        with col_d4:
            st.metric("Validation Logs", f"{db_summary['counts']['validation_logs']:,}")

        st.markdown("---")
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"**Database Location:** `{db_summary['database_path']}`")
            st.markdown(f"**Earliest Sample:** {format_timestamp(db_summary['earliest_timestamp'])}")
            st.markdown(f"**Latest Sample:** {format_timestamp(db_summary['latest_timestamp'])}")
        with col_meta2:
            st.markdown(f"**WAL Journal Mode:** Active (`PRAGMA journal_mode = WAL;`)")
            st.markdown(f"**Foreign Keys:** Enforced (`PRAGMA foreign_keys = ON;`)")
            ret_days = db_summary.get("retention_days")
            st.markdown(f"**Retention Policy:** {f'{ret_days} days' if ret_days else 'Indefinite'}")

        st.markdown("---")
        st.markdown("#### Table Data Explorer")
        table_choice = st.selectbox("Select Table to Inspect", ["system_metrics", "feature_vectors", "validation_logs"])
        table_limit = st.slider("Rows to Display", min_value=5, max_value=100, value=15, step=5)

        if table_choice == "system_metrics":
            records = service.get_historical_metrics(limit=table_limit)
            if records:
                st.dataframe([r.__dict__ for r in reversed(records)], use_container_width=True)
            else:
                st.info("No records in system_metrics.")
        elif table_choice == "feature_vectors":
            features = service.get_historical_features(limit=table_limit)
            if features:
                st.dataframe([f.__dict__ for f in reversed(features)], use_container_width=True)
            else:
                st.info("No records in feature_vectors.")
        elif table_choice == "validation_logs":
            logs = service.get_recent_validation_logs(limit=table_limit)
            if logs:
                st.dataframe([l.__dict__ for l in reversed(logs)], use_container_width=True)
            else:
                st.info("No records in validation_logs.")

    # -------------------------------------------------------------------------
    # Auto-Refresh Handler
    # -------------------------------------------------------------------------
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
