"""Health score and risk overview component."""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from app.dashboard.charts.builders import build_anomaly_gauge, build_health_gauge
from app.dashboard.utils.formatting import format_timestamp
from app.dashboard.utils.theme import get_theme_risk_badge, get_theme_tokens
from app.ml.models import PredictionResult


def render_health_and_risk(
    prediction: Optional[PredictionResult],
    is_model_trained: bool = False,
    theme: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Render health score gauge, anomaly gauge, risk category badge, and explanatory breakdown.

    Args:
        prediction: PredictionResult from PredictionService.
        is_model_trained: Whether prediction originated from a fitted Isolation Forest model.
        theme: Optional active theme ('dark' or 'light').
        **kwargs: Additional legacy or forward-compatible keyword arguments.
    """
    active_mode = theme or kwargs.get("theme")
    tokens = get_theme_tokens(active_mode)

    if prediction is None:
        st.markdown(
            f"""<div class="aiops-empty-state">
                <div style="font-size:28px;">🛡️</div>
                <div class="title">System Health &amp; Risk Evaluation Unavailable</div>
                <div class="desc">No active telemetry feature vectors exist in the database to evaluate health scores. Click <b>"Capture Live Snapshot"</b> in the sidebar or run <code>python run.py</code> to ingest live telemetry.</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # Check for heuristic baseline fallback
    if not is_model_trained or "Heuristic" in prediction.model_name or "fallback" in " ".join(prediction.warnings).lower():
        st.warning(
            "⚠️ **Heuristic Baseline Mode**: A trained Isolation Forest model is not yet loaded. "
            "Health score and risk level are estimated using deterministic hardware saturation rules. "
            "Train an ML model with `python run.py --train` to activate full unsupervised anomaly detection."
        )

    col_gauge, col_anomaly, col_summary = st.columns([1.2, 1.2, 1.6])

    badge = get_theme_risk_badge(prediction.risk_category, theme=active_mode)

    with col_gauge:
        fig_health = build_health_gauge(
            prediction.health_score,
            risk_category=prediction.risk_category,
            theme=active_mode,
        )
        st.plotly_chart(fig_health, width="stretch")

    with col_anomaly:
        fig_anomaly = build_anomaly_gauge(
            prediction.anomaly_score,
            is_anomaly=prediction.is_anomaly,
            theme=active_mode,
        )
        st.plotly_chart(fig_anomaly, width="stretch")

    with col_summary:
        decision_boundary = "Outlier Triggered (Score &gt; 0.50)" if prediction.is_anomaly else "Nominal Cluster (Score &le; 0.50)"
        summary_html = (
            f"<div style='background-color:{tokens.bg_card}; border: 1px solid {tokens.border_color}; "
            f"border-left: 5px solid {badge['color']}; padding: 18px; border-radius: 8px; margin-top: 10px; box-sizing:border-box;'>"
            f"<div style='font-size: 11px; color: {tokens.text_secondary}; text-transform: uppercase; font-weight: 700; letter-spacing: 0.6px;'>"
            f"Failure Risk Assessment"
            f"</div>"
            f"<div style='font-size: 26px; font-weight: 800; color: {badge['color']}; margin-top: 4px;'>"
            f"{badge['icon']} {badge['label']}"
            f"</div>"
            f"<p style='color: {tokens.text_primary}; font-size: 13px; margin-top: 8px; line-height: 1.4;'>"
            f"{badge['description']}"
            f"</p>"
            f"<div style='border-top: 1px solid {tokens.border_color}; padding-top: 10px; margin-top: 10px; font-size: 12px; color: {tokens.text_secondary}; line-height: 1.6;'>"
            f"<div><b>Evaluated By:</b> <span style='color:{tokens.text_primary}; font-weight:600;'>{prediction.model_name} (v{prediction.model_version})</span></div>"
            f"<div><b>Evaluation Time:</b> <span style='color:{tokens.text_primary}; font-variant-numeric:tabular-nums;'>{format_timestamp(prediction.timestamp)}</span></div>"
            f"<div><b>Decision Boundary:</b> <span style='color:{tokens.text_primary}; font-weight:600;'>{decision_boundary}</span></div>"
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
