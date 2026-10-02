"""Health score and risk overview component."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from app.dashboard.charts.builders import build_anomaly_gauge, build_health_gauge
from app.dashboard.utils.formatting import format_timestamp, get_risk_badge
from app.ml.models import PredictionResult


def render_health_and_risk(
    prediction: Optional[PredictionResult],
    is_model_trained: bool = False,
) -> None:
    """Render health score gauge, anomaly gauge, risk category badge, and explanatory breakdown.

    Args:
        prediction: PredictionResult from PredictionService.
        is_model_trained: Whether prediction originated from a fitted Isolation Forest model.
    """
    if prediction is None:
        st.info("ℹ️ System health evaluation is unavailable. No feature vectors exist in the database.")
        return

    # Check for heuristic baseline fallback
    if not is_model_trained or "Heuristic" in prediction.model_name or "fallback" in " ".join(prediction.warnings).lower():
        st.warning(
            "⚠️ **Heuristic Baseline Mode**: A trained Isolation Forest model is not yet loaded. "
            "Health score and risk level are estimated using deterministic hardware saturation rules. "
            "Train an ML model with `python run.py --train` to activate full unsupervised anomaly detection."
        )

    col_gauge, col_anomaly, col_summary = st.columns([1.2, 1.2, 1.6])

    badge = get_risk_badge(prediction.risk_category)

    with col_gauge:
        fig_health = build_health_gauge(
            prediction.health_score,
            risk_category=prediction.risk_category,
        )
        st.plotly_chart(fig_health, use_container_width=True)

    with col_anomaly:
        fig_anomaly = build_anomaly_gauge(
            prediction.anomaly_score,
            is_anomaly=prediction.is_anomaly,
        )
        st.plotly_chart(fig_anomaly, use_container_width=True)

        decision_boundary = "Outlier Triggered (Score &gt; 0.50)" if prediction.is_anomaly else "Nominal Cluster (Score &le; 0.50)"
        summary_html = (
            f"<div style='background-color:{badge['bg']}; border-left: 5px solid {badge['color']}; padding: 16px; border-radius: 6px; margin-top: 20px; box-sizing:border-box;'>"
            f"<div style='font-size: 13px; color: #4B5563; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;'>"
            f"Failure Risk Assessment"
            f"</div>"
            f"<div style='font-size: 26px; font-weight: 800; color: {badge['color']}; margin-top: 4px;'>"
            f"{badge['icon']} {badge['label']}"
            f"</div>"
            f"<p style='color: #374151; font-size: 13px; margin-top: 8px; line-height: 1.4;'>"
            f"{badge['description']}"
            f"</p>"
            f"<div style='border-top: 1px solid rgba(0,0,0,0.08); padding-top: 8px; margin-top: 8px; font-size: 12px; color: #4B5563;'>"
            f"<div><b>Evaluated By:</b> {prediction.model_name} (v{prediction.model_version})</div>"
            f"<div><b>Evaluation Time:</b> {format_timestamp(prediction.timestamp)}</div>"
            f"<div><b>Decision Boundary:</b> {decision_boundary}</div>"
            f"</div>"
            f"</div>"
        )
        st.markdown(summary_html, unsafe_allow_html=True)

    # Warnings / Deductions breakdown if present
    if prediction.warnings:
        with st.expander("🔍 Health Score & Anomaly Deductions Detail", expanded=False):
            for warn in prediction.warnings:
                st.markdown(f"- ⚠️ {warn}")

    # Mandatory Academic Notice
    st.caption(
        "📌 **Academic & Operational Notice**: Anomaly detection identifies behavioral and statistical deviations "
        "relative to baseline telemetry. It does **not** establish that physical hardware or the server will fail."
    )
