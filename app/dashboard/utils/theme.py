"""AIOps Dashboard Design System and Theming Module.

Provides dark and light theme tokens, Plotly figure theming,
and scoped CSS injection for an enterprise operations-center aesthetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

import streamlit as st

ThemeMode = Literal["dark", "light"]


@dataclass(frozen=True)
class ThemeTokens:
    """Design tokens for dashboard visual styling."""

    mode: ThemeMode
    name: str

    # Core background surfaces
    bg_app: str
    bg_card: str
    bg_card_secondary: str
    bg_sidebar: str
    border_color: str
    border_subtle: str

    # Typography colors
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverse: str

    # Accent palette
    accent: str
    accent_hover: str
    accent_bg: str
    accent_border: str

    # Status & severity palette
    color_normal: str
    bg_normal: str
    color_low: str
    bg_low: str
    color_moderate: str
    bg_moderate: str
    color_high: str
    bg_high: str
    color_critical: str
    bg_critical: str

    # Plotly specific tokens
    chart_paper_bg: str
    chart_plot_bg: str
    chart_font_color: str
    chart_grid_color: str
    chart_axis_color: str
    chart_gauge_bg: str
    chart_gauge_border: str


DARK_TOKENS = ThemeTokens(
    mode="dark",
    name="Dark (AIOps Ops-Center)",
    bg_app="#0B0F19",
    bg_card="#151D2C",
    bg_card_secondary="#1E293B",
    bg_sidebar="#111827",
    border_color="#293548",
    border_subtle="#1E293B",
    text_primary="#F8FAFC",
    text_secondary="#94A3B8",
    text_muted="#64748B",
    text_inverse="#0B0F19",
    accent="#38BDF8",
    accent_hover="#0EA5E9",
    accent_bg="rgba(56, 189, 248, 0.12)",
    accent_border="#0284C7",
    color_normal="#10B981",
    bg_normal="rgba(16, 185, 129, 0.16)",
    color_low="#3B82F6",
    bg_low="rgba(59, 130, 246, 0.16)",
    color_moderate="#F59E0B",
    bg_moderate="rgba(245, 158, 11, 0.16)",
    color_high="#F97316",
    bg_high="rgba(249, 115, 22, 0.18)",
    color_critical="#EF4444",
    bg_critical="rgba(239, 68, 68, 0.22)",
    chart_paper_bg="rgba(0,0,0,0)",
    chart_plot_bg="rgba(0,0,0,0)",
    chart_font_color="#F8FAFC",
    chart_grid_color="#293548",
    chart_axis_color="#475569",
    chart_gauge_bg="#151D2C",
    chart_gauge_border="#293548",
)

LIGHT_TOKENS = ThemeTokens(
    mode="light",
    name="Light (Enterprise Neutral)",
    bg_app="#F8FAFC",
    bg_card="#FFFFFF",
    bg_card_secondary="#F1F5F9",
    bg_sidebar="#F1F5F9",
    border_color="#E2E8F0",
    border_subtle="#CBD5E1",
    text_primary="#0F172A",
    text_secondary="#475569",
    text_muted="#94A3B8",
    text_inverse="#FFFFFF",
    accent="#0284C7",
    accent_hover="#0369A1",
    accent_bg="rgba(2, 132, 199, 0.08)",
    accent_border="#0284C7",
    color_normal="#10B981",
    bg_normal="#E6F4EA",
    color_low="#3B82F6",
    bg_low="#E8F0FE",
    color_moderate="#F59E0B",
    bg_moderate="#FEF3C7",
    color_high="#F97316",
    bg_high="#FFEDD5",
    color_critical="#EF4444",
    bg_critical="#FEE2E2",
    chart_paper_bg="rgba(0,0,0,0)",
    chart_plot_bg="rgba(0,0,0,0)",
    chart_font_color="#1E293B",
    chart_grid_color="#E2E8F0",
    chart_axis_color="#CBD5E1",
    chart_gauge_bg="#F1F5F9",
    chart_gauge_border="#E2E8F0",
)


def get_theme_tokens(
    mode: Optional[str] = None,
    theme: Optional[str] = None,
    **kwargs: Any,
) -> ThemeTokens:
    """Retrieve the ThemeTokens instance for the specified mode or theme.

    Accepts mode or theme keyword argument.
    If both are None, reads from st.session_state['theme'] (defaulting to 'dark').
    """
    target = theme if theme is not None else mode
    if target is None:
        target = kwargs.get("theme") or kwargs.get("mode")
    if target is None:
        try:
            target = st.session_state.get("theme", "dark")
        except Exception:
            target = "dark"

    normalized = str(target).lower()
    if "light" in normalized:
        return LIGHT_TOKENS
    return DARK_TOKENS


def get_current_theme() -> ThemeMode:
    """Return the active theme string ('dark' or 'light')."""
    try:
        current = st.session_state.get("theme", "dark")
        return "light" if "light" in str(current).lower() else "dark"
    except Exception:
        return "dark"


def set_theme(mode: ThemeMode) -> None:
    """Set the active theme in session state."""
    st.session_state["theme"] = mode


def get_theme_risk_badge(
    category: Any,
    mode: Optional[str] = None,
    theme: Optional[str] = None,
    **kwargs: Any,
) -> dict[str, str]:
    """Retrieve theme-aware styling dictionary for a risk category badge.

    Accepts both mode and theme keyword arguments.
    Falls back to st.session_state['theme'] if neither is provided.
    """
    target = theme if theme is not None else mode
    if target is None:
        target = kwargs.get("theme") or kwargs.get("mode")
    tokens = get_theme_tokens(theme=target)
    from app.dashboard.utils.formatting import get_risk_badge
    base = get_risk_badge(category)

    # Use theme-optimized background for dark mode to prevent glare
    cat_str = str(base.get("label", "")).lower()
    if "normal" in cat_str:
        bg = tokens.bg_normal
    elif "low" in cat_str:
        bg = tokens.bg_low
    elif "moderate" in cat_str:
        bg = tokens.bg_moderate
    elif "high" in cat_str:
        bg = tokens.bg_high
    elif "critical" in cat_str:
        bg = tokens.bg_critical
    else:
        bg = tokens.bg_card_secondary

    return {
        "label": base["label"],
        "color": base["color"],
        "bg": bg,
        "icon": base["icon"],
        "description": base["description"],
    }


def generate_theme_css(tokens: ThemeTokens) -> str:
    """Generate scoped CSS variables and component styles for the active theme."""
    return f"""
<style>
/* ==========================================================================
   AI-Based Server Health Monitoring - AIOps Command Center ({tokens.mode.upper()})
   ========================================================================== */
:root {{
    --bg-app: {tokens.bg_app};
    --bg-card: {tokens.bg_card};
    --bg-card-sec: {tokens.bg_card_secondary};
    --bg-sidebar: {tokens.bg_sidebar};
    --border-color: {tokens.border_color};
    --border-subtle: {tokens.border_subtle};
    --text-primary: {tokens.text_primary};
    --text-secondary: {tokens.text_secondary};
    --text-muted: {tokens.text_muted};
    --accent: {tokens.accent};
    --accent-hover: {tokens.accent_hover};
    --accent-bg: {tokens.accent_bg};
}}

/* Main App Canvas */
.stApp {{
    background-color: {tokens.bg_app} !important;
    color: {tokens.text_primary} !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}}

/* Sidebar Container */
[data-testid="stSidebar"] {{
    background-color: {tokens.bg_sidebar} !important;
    border-right: 1px solid {tokens.border_color} !important;
}}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {{
    color: {tokens.text_primary} !important;
}}

/* Metric Cards Default Overrides */
[data-testid="stMetric"] {{
    background-color: {tokens.bg_card} !important;
    border: 1px solid {tokens.border_color} !important;
    border-radius: 8px !important;
    padding: 14px 18px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25) !important;
    transition: transform 0.15s ease, border-color 0.15s ease !important;
    min-height: 105px !important;
}}
[data-testid="stMetric"]:hover {{
    border-color: {tokens.accent} !important;
    transform: translateY(-1px) !important;
}}
[data-testid="stMetric"] label,
[data-testid="stMetric"] [data-testid="stMetricLabel"] {{
    color: {tokens.text_secondary} !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.6px !important;
}}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    color: {tokens.text_primary} !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums !important;
}}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-size: 12px !important;
    font-weight: 500 !important;
    color: {tokens.text_muted} !important;
}}

/* Expanders */
.streamlit-expanderHeader {{
    background-color: {tokens.bg_card} !important;
    color: {tokens.text_primary} !important;
    border: 1px solid {tokens.border_color} !important;
    border-radius: 6px !important;
}}
.streamlit-expanderContent {{
    background-color: {tokens.bg_card} !important;
    border: 1px solid {tokens.border_color} !important;
    border-top: none !important;
    border-bottom-left-radius: 6px !important;
    border-bottom-right-radius: 6px !important;
    color: {tokens.text_primary} !important;
}}

/* Form elements & buttons */
button[kind="primary"] {{
    background-color: {tokens.accent} !important;
    color: {tokens.text_inverse} !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    transition: background-color 0.15s ease;
}}
button[kind="primary"]:hover {{
    background-color: {tokens.accent_hover} !important;
}}
button[kind="secondary"] {{
    background-color: {tokens.bg_card_secondary} !important;
    color: {tokens.text_primary} !important;
    border: 1px solid {tokens.border_color} !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}}
button[kind="secondary"]:hover {{
    border-color: {tokens.accent} !important;
}}

/* Text & Headings */
h1, h2, h3, h4, h5, h6 {{
    color: {tokens.text_primary} !important;
    letter-spacing: -0.3px;
}}
p, span, label {{
    color: {tokens.text_primary};
}}

/* Alerts and Status Banners */
[data-testid="stAlert"] {{
    border-radius: 6px !important;
    border: 1px solid {tokens.border_color} !important;
}}

/* DataFrames */
[data-testid="stDataFrame"] {{
    border: 1px solid {tokens.border_color} !important;
    border-radius: 6px !important;
    background-color: {tokens.bg_card} !important;
}}

/* Custom AIOps Command Center Components */
.aiops-card {{
    background-color: {tokens.bg_card};
    border: 1px solid {tokens.border_color};
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 14px;
    box-sizing: border-box;
}}
.aiops-card-secondary {{
    background-color: {tokens.bg_card_secondary};
    border: 1px solid {tokens.border_color};
    border-radius: 6px;
    padding: 12px;
    box-sizing: border-box;
}}
.aiops-badge {{
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
.aiops-empty-state {{
    background-color: {tokens.bg_card};
    border: 1px dashed {tokens.border_color};
    border-radius: 8px;
    padding: 28px 20px;
    text-align: center;
    margin: 12px 0;
}}
.aiops-empty-state .title {{
    font-size: 14px;
    font-weight: 700;
    color: {tokens.text_primary};
    margin-top: 8px;
}}
.aiops-empty-state .desc {{
    font-size: 12px;
    color: {tokens.text_secondary};
    margin-top: 4px;
    max-width: 440px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.4;
}}
</style>
"""


def apply_theme_css(
    mode: Optional[str] = None,
    theme: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Inject active theme CSS into the Streamlit session."""
    target = theme if theme is not None else mode
    if target is None:
        target = kwargs.get("theme") or kwargs.get("mode")
    tokens = get_theme_tokens(theme=target)
    css_str = generate_theme_css(tokens)
    st.markdown(css_str, unsafe_allow_html=True)
