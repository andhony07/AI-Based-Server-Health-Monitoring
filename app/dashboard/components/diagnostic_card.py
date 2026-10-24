"""Diagnostic report and explainable recommendations component for Streamlit."""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from app.dashboard.utils.theme import get_theme_tokens
from app.ml.diagnostics import DiagnosticReport, EvidenceLevel


def render_diagnostic_report(
    report: Optional[DiagnosticReport],
    theme: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Render explainable, evidence-based diagnostic recommendations and findings.

    Args:
        report: DiagnosticReport from DiagnosticEngine.
        theme: Optional active theme ('dark' or 'light').
        **kwargs: Additional legacy or forward-compatible keyword arguments.
    """
    active_mode = theme or kwargs.get("theme")
    tokens = get_theme_tokens(active_mode)

    if report is None:
        st.markdown(
            f"""<div class="aiops-empty-state">
                <div style="font-size:28px;">🩺</div>
                <div class="title">Diagnostic Report Unavailable</div>
                <div class="desc">No diagnostic findings or root-cause evaluations are available for the current telemetry state. Capture a snapshot or execute an anomaly simulation to generate explainable findings.</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    # Executive Headline Banner
    if report.critical_count > 0:
        st.error(f"### {report.summary_headline}")
    elif report.warning_count > 0:
        st.warning(f"### {report.summary_headline}")
    else:
        st.success(f"### {report.summary_headline}")

    health_score_str = f"&nbsp;|&nbsp; **Health Score:** `{report.overall_health_score:.1f}/100`" if report.overall_health_score is not None else ""
    st.markdown(
        f"**Primary Concern:** `{report.primary_concern or 'Nominal'}` &nbsp;|&nbsp; "
        f"**Evaluated Risk:** `{report.risk_category.value}` {health_score_str}"
    )

    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

    # Theme-aware severity colors and badges
    if tokens.mode == "dark":
        sev_colors = {
            EvidenceLevel.CRITICAL: ("#EF4444", "rgba(239, 68, 68, 0.20)", "🔴"),
            EvidenceLevel.HIGH: ("#F97316", "rgba(249, 115, 22, 0.20)", "🟠"),
            EvidenceLevel.MODERATE: ("#F59E0B", "rgba(245, 158, 11, 0.20)", "🟡"),
            EvidenceLevel.LOW: ("#38BDF8", "rgba(56, 189, 248, 0.20)", "🔵"),
            EvidenceLevel.INFO: ("#10B981", "rgba(16, 185, 129, 0.20)", "🟢"),
        }
    else:
        sev_colors = {
            EvidenceLevel.CRITICAL: ("#DC2626", "#FEE2E2", "🔴"),
            EvidenceLevel.HIGH: ("#EA580C", "#FFEDD5", "🟠"),
            EvidenceLevel.MODERATE: ("#D97706", "#FEF3C7", "🟡"),
            EvidenceLevel.LOW: ("#2563EB", "#EFF6FF", "🔵"),
            EvidenceLevel.INFO: ("#059669", "#D1FAE5", "🟢"),
        }

    # 1. Dedicated Empirical Telemetry Evidence Panel (Observed Facts)
    all_evidence = []
    for rec in report.recommendations:
        for ev in rec.evidence:
            all_evidence.append({
                "Subsystem": rec.category.value,
                "Signal / Metric": ev.metric_name,
                "Observed Telemetry": str(ev.observed_value),
                "Baseline / Threshold": ev.threshold,
                "Evidence Severity": ev.level.value,
                "Significance Explanation": ev.description,
            })

    if all_evidence:
        st.markdown(
            f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px; margin: 12px 0 6px 0;'>"
            f"🔍 Empirical Telemetry Evidence (Observed Hardware &amp; Signal Measurements)</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(all_evidence, width="stretch", hide_index=True)
        st.caption("ℹ️ *Observed telemetry represents empirical sensor measurements recorded during collection, distinct from probabilistic ML anomaly predictions.*")

    # 2. Structured Diagnostic Findings & Remediation Sequence (Hypotheses & Action Plan)
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:8px;'>"
        f"🛠️ Explainable Diagnostic Recommendations &amp; Prioritized Remediation Plan</div>",
        unsafe_allow_html=True,
    )

    if not report.recommendations:
        st.markdown(
            f"""<div style="background-color:{tokens.bg_card}; border: 1px solid {tokens.border_color}; border-radius:8px; padding:18px; text-align:center;">
                <div style="color:{tokens.color_normal}; font-weight:700; font-size:14px;">🟢 All Subsystems Nominal</div>
                <div style="color:{tokens.text_secondary}; font-size:12px; margin-top:4px;">No critical or warning-level operational anomalies detected across host hardware and processes.</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    for idx, rec in enumerate(report.recommendations):
        color, bg, icon = sev_colors.get(rec.severity, ("#64748B", tokens.bg_card_secondary, "⚪"))
        card_title = f"{icon} [{rec.severity.value}] {rec.title}"

        with st.expander(card_title, expanded=(idx == 0 or rec.severity in (EvidenceLevel.CRITICAL, EvidenceLevel.HIGH))):
            # Domain & Target Header Chips
            target_str = rec.target_component or "Host Subsystem"
            st.markdown(
                f"<div style='margin-bottom:8px; display:flex; align-items:center; gap:8px; flex-wrap:wrap;'>"
                f"<span style='background-color:{bg}; color:{color}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; border:1px solid {color}40;'>"
                f"{rec.category.value} Domain"
                f"</span>"
                f"<span style='background-color:{tokens.bg_card_secondary}; color:{tokens.text_secondary}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; border:1px solid {tokens.border_color};'>"
                f"Target: {target_str}"
                f"</span>"
                f"<span style='background-color:{tokens.bg_card_secondary}; color:{tokens.text_muted}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:500; border:1px solid {tokens.border_color};'>"
                f"Rule ID: {rec.id}"
                f"</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Operational Summary
            st.markdown(f"**Operational Summary:** {rec.summary}")

            # Root-Cause Hypothesis (Clearly distinguished as an unconfirmed engineering hypothesis)
            st.markdown(
                f"<div style='background-color:{tokens.bg_card_secondary}; border-left:3px solid {tokens.accent}; padding:10px 14px; border-radius:4px; margin:10px 0;'>"
                f"<div style='font-size:11px; font-weight:700; color:{tokens.accent}; text-transform:uppercase; letter-spacing:0.5px;'>🔬 Root-Cause Hypothesis (Unconfirmed Diagnostic Analysis)</div>"
                f"<div style='font-size:13px; color:{tokens.text_primary}; margin-top:3px; line-height:1.4;'><i>{rec.root_cause_hypothesis}</i></div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Prioritized Remediation Sequence
            if rec.remediation_steps:
                st.markdown(
                    f"<div style='font-size:12px; font-weight:700; color:{tokens.text_secondary}; text-transform:uppercase; letter-spacing:0.5px; margin:12px 0 6px 0;'>"
                    f"Prioritized Remediation Sequence</div>",
                    unsafe_allow_html=True,
                )
                for s_idx, step in enumerate(rec.remediation_steps, 1):
                    st.markdown(
                        f"<div style='display:flex; align-items:flex-start; gap:8px; margin-bottom:6px; font-size:13px;'>"
                        f"<span style='background-color:{tokens.bg_card_secondary}; color:{tokens.text_primary}; border:1px solid {tokens.border_color}; padding:1px 6px; border-radius:3px; font-size:11px; font-weight:700;'>Step {s_idx}</span>"
                        f"<span style='color:{tokens.text_primary};'>{step}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
