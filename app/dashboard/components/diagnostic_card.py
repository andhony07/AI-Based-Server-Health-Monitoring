"""Diagnostic report and explainable recommendations component for Streamlit."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from app.ml.diagnostics import DiagnosticReport, EvidenceLevel


def render_diagnostic_report(report: Optional[DiagnosticReport]) -> None:
    """Render explainable, evidence-based diagnostic recommendations and findings.

    Args:
        report: DiagnosticReport from DiagnosticEngine.
    """
    if report is None:
        st.info("ℹ️ No diagnostic report available for current telemetry state.")
        return

    # Executive Headline Banner
    if report.critical_count > 0:
        st.error(f"### {report.summary_headline}")
    elif report.warning_count > 0:
        st.warning(f"### {report.summary_headline}")
    else:
        st.success(f"### {report.summary_headline}")

    st.markdown(
        f"**Primary Concern:** `{report.primary_concern or 'Nominal'}` &nbsp;|&nbsp; "
        f"**Evaluated Risk:** `{report.risk_category.value}` &nbsp;|&nbsp; "
        f"**Health Score:** `{report.overall_health_score:.1f}/100`" if report.overall_health_score is not None else ""
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Render each diagnostic finding
    sev_colors = {
        EvidenceLevel.CRITICAL: ("#EF4444", "#FEE2E2", "🔴"),
        EvidenceLevel.HIGH: ("#F97316", "#FFEDD5", "🟠"),
        EvidenceLevel.MODERATE: ("#F59E0B", "#FEF3C7", "🟡"),
        EvidenceLevel.LOW: ("#3B82F6", "#EFF6FF", "🔵"),
        EvidenceLevel.INFO: ("#10B981", "#D1FAE5", "🟢"),
    }

    for idx, rec in enumerate(report.recommendations):
        color, bg, icon = sev_colors.get(rec.severity, ("#64748B", "#F1F5F9", "⚪"))
        card_title = f"{icon} [{rec.severity.value}] {rec.title}"

        with st.expander(card_title, expanded=(idx == 0 or rec.severity == EvidenceLevel.CRITICAL)):
            st.markdown(f"**Affected Domain:** `{rec.category.value}` &nbsp;&nbsp;|&nbsp;&nbsp; **Target Component:** `{rec.target_component or 'System'}`")
            st.markdown(f"**Operational Summary:** {rec.summary}")
            st.markdown(f"**Root-Cause Hypothesis:** *{rec.root_cause_hypothesis}*")

            # Evidence Section
            if rec.evidence:
                st.markdown("##### 🔍 Empirical Telemetry Evidence")
                ev_data = [
                    {
                        "Metric / Signal": e.metric_name,
                        "Observed Telemetry": str(e.observed_value),
                        "Baseline / Threshold": e.threshold,
                        "Significance": e.description,
                    }
                    for e in rec.evidence
                ]
                st.dataframe(ev_data, width="stretch", hide_index=True)

            # Remediation Guidance
            if rec.remediation_steps:
                st.markdown("##### 🛠️ Prioritized Remediation Steps")
                for s_idx, step in enumerate(rec.remediation_steps, 1):
                    st.markdown(f"{s_idx}. {step}")
