"""Status header component for the server health monitoring dashboard."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import streamlit as st

from app.dashboard.utils.formatting import format_timestamp


def render_status_header(
    last_updated: Optional[datetime] = None,
    is_monitoring: bool = False,
    model_name: str = "IsolationForestDetector",
    is_model_trained: bool = False,
    db_record_count: int = 0,
) -> None:
    """Render top-level executive banner with system status indicators.

    Args:
        last_updated: Timestamp of the most recent telemetry sample.
        is_monitoring: Whether live background collection is running.
        model_name: Active ML model identifier.
        is_model_trained: True if fitted ML checkpoint loaded, False for heuristic baseline.
        db_record_count: Total persisted metric rows in SQLite.
    """
    col_title, col_status = st.columns([3, 2])

    with col_title:
        st.markdown(
            """
            <h2 style='margin-bottom: 2px; color: #1E293B;'>
                🖥️ AI Server Health & Failure Risk Monitor
            </h2>
            <p style='color: #64748B; font-size: 14px; margin-top: 0;'>
                Real-Time OS Telemetry, Isolation Forest Anomaly Detection & Risk Analysis
            </p>
            """,
            unsafe_allow_html=True,
        )

    with col_status:
        # Status pills
        monitor_pill = (
            "<span style='background-color:#D1FAE5; color:#065F46; padding:4px 8px; border-radius:12px; font-size:12px; font-weight:600;'>🟢 Monitoring Active</span>"
            if is_monitoring
            else "<span style='background-color:#F3F4F6; color:#4B5563; padding:4px 8px; border-radius:12px; font-size:12px; font-weight:600;'>⚪ Standby / Static</span>"
        )

        model_pill = (
            f"<span style='background-color:#DBEAFE; color:#1E40AF; padding:4px 8px; border-radius:12px; font-size:12px; font-weight:600;'>🤖 ML: {model_name}</span>"
            if is_model_trained
            else "<span style='background-color:#FEF3C7; color:#92400E; padding:4px 8px; border-radius:12px; font-size:12px; font-weight:600;'>⚠️ Heuristic Baseline</span>"
        )

        db_pill = f"<span style='background-color:#F1F5F9; color:#334155; padding:4px 8px; border-radius:12px; font-size:12px; font-weight:600;'>🗄️ SQLite: {db_record_count:,} samples</span>"

        st.markdown(
            f"""
            <div style='text-align: right; padding-top: 8px;'>
                {monitor_pill} &nbsp; {model_pill} &nbsp; {db_pill}
                <div style='color: #94A3B8; font-size: 12px; margin-top: 6px;'>
                    Last Telemetry: <b>{format_timestamp(last_updated)}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin-top: 8px; margin-bottom: 20px; border-color: #E2E8F0;'>", unsafe_allow_html=True)
