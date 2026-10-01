"""Plotly chart builders for interactive system telemetry and health risk visualization."""

from __future__ import annotations

from typing import Any, Optional, Union

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.database.models import SystemMetricRecord
from app.ml.models import RiskCategory


def build_health_gauge(
    health_score: Optional[float],
    risk_category: Union[RiskCategory, str] = "Normal",
    title: str = "System Health Score",
) -> go.Figure:
    """Construct an interactive Plotly radial gauge displaying system health (0-100).

    Args:
        health_score: Float health score between 0.0 and 100.0 or None.
        risk_category: Associated risk tier.
        title: Gauge header title.

    Returns:
        Configured plotly.graph_objects.Figure.
    """
    val = float(health_score) if health_score is not None else 0.0
    display_text = f"{val:.1f}" if health_score is not None else "N/A"

    cat_name = (
        risk_category.value
        if isinstance(risk_category, RiskCategory)
        else str(risk_category).capitalize()
    )

    bar_color = "#10B981"
    if cat_name == "Critical":
        bar_color = "#EF4444"
    elif cat_name == "High":
        bar_color = "#F97316"
    elif cat_name == "Moderate":
        bar_color = "#F59E0B"
    elif cat_name == "Low":
        bar_color = "#3B82F6"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            number={"suffix": " / 100", "font": {"size": 28, "color": bar_color}},
            title={"text": f"<b>{title}</b><br><span style='font-size:13px; color:#6B7280;'>Risk: {cat_name}</span>", "font": {"size": 16}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#9CA3AF"},
                "bar": {"color": bar_color, "thickness": 0.3},
                "bgcolor": "#F3F4F6",
                "borderwidth": 1,
                "bordercolor": "#E5E7EB",
                "steps": [
                    {"range": [0, 25], "color": "rgba(239, 68, 68, 0.15)"},    # Critical Red
                    {"range": [25, 45], "color": "rgba(249, 115, 22, 0.15)"},  # High Orange
                    {"range": [45, 65], "color": "rgba(245, 158, 11, 0.15)"},  # Moderate Amber
                    {"range": [65, 80], "color": "rgba(59, 130, 246, 0.15)"},  # Low Blue
                    {"range": [80, 100], "color": "rgba(16, 185, 129, 0.15)"}, # Normal Green
                ],
                "threshold": {
                    "line": {"color": "#EF4444", "width": 3},
                    "thickness": 0.8,
                    "value": 25.0,
                },
            },
        )
    )

    fig.update_layout(
        height=260,
        margin=dict(l=25, r=25, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def build_anomaly_gauge(
    anomaly_score: Optional[float],
    is_anomaly: bool = False,
    title: str = "Calibrated Anomaly Score",
) -> go.Figure:
    """Construct an indicator gauge for the calibrated anomaly score (0.0 to 1.0).

    Args:
        anomaly_score: Score between 0.0 and 1.0.
        is_anomaly: Boolean flag indicating if anomaly boundary was exceeded.
        title: Gauge header title.

    Returns:
        Configured plotly.graph_objects.Figure.
    """
    val = float(anomaly_score) if anomaly_score is not None else 0.0
    status_label = "Anomaly Detected" if is_anomaly else "Nominal Behavior"
    status_color = "#EF4444" if is_anomaly else "#10B981"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=val,
            number={"valueformat": ".3f", "font": {"size": 28, "color": status_color}},
            title={"text": f"<b>{title}</b><br><span style='font-size:13px; color:{status_color};'>{status_label}</span>", "font": {"size": 16}},
            gauge={
                "axis": {"range": [0.0, 1.0], "tickwidth": 1, "tickcolor": "#9CA3AF"},
                "bar": {"color": status_color, "thickness": 0.3},
                "bgcolor": "#F3F4F6",
                "borderwidth": 1,
                "bordercolor": "#E5E7EB",
                "steps": [
                    {"range": [0.0, 0.35], "color": "rgba(16, 185, 129, 0.15)"},
                    {"range": [0.35, 0.55], "color": "rgba(59, 130, 246, 0.15)"},
                    {"range": [0.55, 0.75], "color": "rgba(245, 158, 11, 0.15)"},
                    {"range": [0.75, 1.0], "color": "rgba(239, 68, 68, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": "#DC2626", "width": 3},
                    "thickness": 0.8,
                    "value": 0.50,
                },
            },
        )
    )

    fig.update_layout(
        height=260,
        margin=dict(l=25, r=25, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def build_resource_breakdown_bar(metric: Optional[SystemMetricRecord]) -> go.Figure:
    """Build a comparative bar chart comparing CPU, RAM, and Disk utilization percentages.

    Args:
        metric: Latest SystemMetricRecord.

    Returns:
        Plotly Figure.
    """
    labels = ["CPU", "Memory (RAM)", "Disk Storage"]
    values = [
        metric.cpu_percent if metric and metric.cpu_percent is not None else 0.0,
        metric.memory_percent if metric and metric.memory_percent is not None else 0.0,
        metric.disk_percent if metric and metric.disk_percent is not None else 0.0,
    ]

    colors = []
    for v in values:
        if v >= 95.0:
            colors.append("#EF4444")
        elif v >= 80.0:
            colors.append("#F59E0B")
        else:
            colors.append("#10B981")

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            text=[f"{v:.1f}%" for v in values],
            textposition="auto",
            marker=dict(color=colors, line=dict(color="#374151", width=1)),
            width=0.45,
        )
    )

    # Reference lines for warning (80%) and critical (95%)
    fig.add_hline(y=80, line_dash="dot", line_color="#F59E0B", annotation_text="Warning (80%)", annotation_position="top right")
    fig.add_hline(y=95, line_dash="dash", line_color="#EF4444", annotation_text="Critical (95%)", annotation_position="top right")

    fig.update_layout(
        title="<b>Current Hardware Resource Saturation</b>",
        yaxis=dict(title="Utilization (%)", range=[0, 105]),
        xaxis=dict(title=""),
        height=320,
        margin=dict(l=40, r=40, t=50, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def build_multi_metric_timeseries(
    records: list[SystemMetricRecord],
    selected_metrics: Optional[list[str]] = None,
) -> go.Figure:
    """Construct an interactive multi-metric time-series line chart.

    Args:
        records: Chronologically sorted list of SystemMetricRecord instances.
        selected_metrics: List of metric series to plot. Defaults to CPU, RAM, Disk.

    Returns:
        Plotly Figure.
    """
    if not records:
        fig = go.Figure()
        fig.add_annotation(
            text="No historical telemetry available for the selected range.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#9CA3AF"),
        )
        fig.update_layout(height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    metrics_to_plot = selected_metrics or [
        "CPU Utilization (%)",
        "RAM Utilization (%)",
        "Disk Utilization (%)",
    ]

    has_throughput = any("Throughput" in m or "KB/s" in m for m in metrics_to_plot)

    # Use secondary y-axis if throughput (KB/s) is plotted alongside percentages (%)
    if has_throughput:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    timestamps = [r.timestamp for r in records]

    colors = {
        "CPU Utilization (%)": "#3B82F6",    # Blue
        "RAM Utilization (%)": "#8B5CF6",    # Purple
        "Disk Utilization (%)": "#10B981",   # Green
        "Network TX (KB/s)": "#F59E0B",      # Amber
        "Network RX (KB/s)": "#EC4899",      # Pink
        "Active Processes": "#6B7280",       # Gray
    }

    if "CPU Utilization (%)" in metrics_to_plot:
        cpus = [r.cpu_percent if r.cpu_percent is not None else 0.0 for r in records]
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=cpus,
                mode="lines+markers",
                name="CPU (%)",
                line=dict(color=colors["CPU Utilization (%)"], width=2),
                marker=dict(size=4),
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>CPU: %{y:.1f}%<extra></extra>",
            )
        )

    if "RAM Utilization (%)" in metrics_to_plot:
        rams = [r.memory_percent if r.memory_percent is not None else 0.0 for r in records]
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=rams,
                mode="lines+markers",
                name="RAM (%)",
                line=dict(color=colors["RAM Utilization (%)"], width=2),
                marker=dict(size=4),
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>RAM: %{y:.1f}%<extra></extra>",
            )
        )

    if "Disk Utilization (%)" in metrics_to_plot:
        disks = [r.disk_percent if r.disk_percent is not None else 0.0 for r in records]
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=disks,
                mode="lines",
                name="Disk (%)",
                line=dict(color=colors["Disk Utilization (%)"], width=2, dash="dash"),
                hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>Disk: %{y:.1f}%<extra></extra>",
            )
        )

    if "Network TX (KB/s)" in metrics_to_plot:
        txs = [(r.network_bytes_sent_per_sec or 0.0) / 1024.0 for r in records]
        trace_tx = go.Scatter(
            x=timestamps,
            y=txs,
            mode="lines",
            name="Network TX (KB/s)",
            line=dict(color=colors["Network TX (KB/s)"], width=1.5),
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>TX: %{y:.1f} KB/s<extra></extra>",
        )
        if has_throughput:
            fig.add_trace(trace_tx, secondary_y=True)
        else:
            fig.add_trace(trace_tx)

    if "Network RX (KB/s)" in metrics_to_plot:
        rxs = [(r.network_bytes_recv_per_sec or 0.0) / 1024.0 for r in records]
        trace_rx = go.Scatter(
            x=timestamps,
            y=rxs,
            mode="lines",
            name="Network RX (KB/s)",
            line=dict(color=colors["Network RX (KB/s)"], width=1.5),
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>RX: %{y:.1f} KB/s<extra></extra>",
        )
        if has_throughput:
            fig.add_trace(trace_rx, secondary_y=True)
        else:
            fig.add_trace(trace_rx)

    if "Active Processes" in metrics_to_plot:
        procs = [r.process_count if r.process_count is not None else 0 for r in records]
        trace_proc = go.Scatter(
            x=timestamps,
            y=procs,
            mode="lines",
            name="Processes",
            line=dict(color=colors["Active Processes"], width=1.5, dash="dot"),
            hovertemplate="%{x|%Y-%m-%d %H:%M:%S}<br>Procs: %{y}<extra></extra>",
        )
        if has_throughput:
            fig.add_trace(trace_proc, secondary_y=True)
        else:
            fig.add_trace(trace_proc)

    fig.update_layout(
        title="<b>Historical System Telemetry Over Time</b>",
        xaxis=dict(title="Timestamp (UTC)", showgrid=True, gridcolor="#E5E7EB"),
        yaxis=dict(title="Utilization (%)", range=[0, 105], showgrid=True, gridcolor="#E5E7EB"),
        height=420,
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, sans-serif"),
    )

    if has_throughput:
        fig.update_yaxes(title_text="Throughput (KB/s) / Count", secondary_y=True, showgrid=False)

    return fig


def build_anomaly_scatter_chart(anomalies: list[dict[str, Any]]) -> go.Figure:
    """Build a scatter chart displaying anomaly scores and risk tiers across historical samples.

    Args:
        anomalies: List of anomaly dictionaries produced by DashboardService.get_historical_anomalies().

    Returns:
        Plotly Figure.
    """
    if not anomalies:
        fig = go.Figure()
        fig.add_annotation(
            text="No anomaly history records available.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#9CA3AF"),
        )
        fig.update_layout(height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    timestamps = [a["timestamp"] for a in anomalies]
    scores = [a["anomaly_score"] for a in anomalies]
    categories = [a["risk_category"] for a in anomalies]

    color_map = {
        "Normal": "#10B981",
        "Low": "#3B82F6",
        "Moderate": "#F59E0B",
        "High": "#F97316",
        "Critical": "#EF4444",
    }
    point_colors = [color_map.get(c, "#6B7280") for c in categories]
    sizes = [max(8, int(s * 22)) for s in scores]

    hover_texts = [
        f"Time: {a['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}<br>"
        f"Risk: {a['risk_category']}<br>"
        f"Anomaly Score: {a['anomaly_score']:.4f}<br>"
        f"Health: {a['health_score']:.1f}/100<br>"
        f"CPU: {a.get('cpu_percent', 0.0):.1f}% | RAM: {a.get('memory_percent', 0.0):.1f}%<br>"
        f"Model: {a.get('model_name', 'N/A')}"
        for a in anomalies
    ]

    fig = go.Figure(
        go.Scatter(
            x=timestamps,
            y=scores,
            mode="markers",
            marker=dict(
                size=sizes,
                color=point_colors,
                opacity=0.85,
                line=dict(color="#1F2937", width=1),
            ),
            text=hover_texts,
            hoverinfo="text",
            name="Anomaly Score",
        )
    )

    # Reference line for anomaly decision threshold (0.50)
    fig.add_hline(
        y=0.50,
        line_dash="dash",
        line_color="#EF4444",
        annotation_text="Decision Boundary (0.50)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="<b>Historical Anomaly Evaluation Timeline</b>",
        xaxis=dict(title="Timestamp (UTC)", showgrid=True, gridcolor="#E5E7EB"),
        yaxis=dict(title="Calibrated Anomaly Score", range=[0.0, 1.05], showgrid=True, gridcolor="#E5E7EB"),
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )
    return fig
