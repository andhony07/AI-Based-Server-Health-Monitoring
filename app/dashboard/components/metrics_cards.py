"""Telemetry metric cards component."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from app.dashboard.utils.formatting import (
    format_bytes,
    format_percent,
    format_throughput,
    get_resource_status,
)
from app.database.models import SystemMetricRecord


def render_metric_cards(metric: Optional[SystemMetricRecord]) -> None:
    """Render executive metric cards for CPU, Memory, Disk, Network, and Processes.

    Args:
        metric: Most recent SystemMetricRecord instance or None if database is empty.
    """
    if metric is None:
        st.warning("⚠️ No system telemetry records found in the database. Start monitoring or capture a snapshot below.")
        return

    # Status assessments
    cpu_status, cpu_color, cpu_icon = get_resource_status(metric.cpu_percent, warn_thresh=80.0, crit_thresh=95.0)
    ram_status, ram_color, ram_icon = get_resource_status(metric.memory_percent, warn_thresh=85.0, crit_thresh=95.0)
    disk_status, disk_color, disk_icon = get_resource_status(metric.disk_percent, warn_thresh=90.0, crit_thresh=95.0)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        cpu_val = format_percent(metric.cpu_percent)
        cores_info = f"{metric.cpu_logical_cores or 0} Cores"
        st.metric(
            label=f"{cpu_icon} CPU Load",
            value=cpu_val,
            delta=cores_info,
            delta_color="off",
            help=f"Status: {cpu_status}. Thresholds: Warning >80%, Critical >95%",
        )

    with col2:
        ram_val = format_percent(metric.memory_percent)
        ram_used = format_bytes(metric.memory_used_bytes)
        ram_total = format_bytes(metric.memory_total_bytes)
        st.metric(
            label=f"{ram_icon} Memory (RAM)",
            value=ram_val,
            delta=f"{ram_used} / {ram_total}",
            delta_color="off",
            help=f"Status: {ram_status}. Thresholds: Warning >85%, Critical >95%",
        )

    with col3:
        disk_val = format_percent(metric.disk_percent)
        disk_used = format_bytes(metric.disk_used_bytes)
        disk_total = format_bytes(metric.disk_total_bytes)
        st.metric(
            label=f"{disk_icon} Disk Storage",
            value=disk_val,
            delta=f"{disk_used} / {disk_total}",
            delta_color="off",
            help=f"Status: {disk_status}. Thresholds: Warning >90%, Critical >95%",
        )

    with col4:
        tx_kbps = (metric.network_bytes_sent_per_sec or 0.0) / 1024.0
        rx_kbps = (metric.network_bytes_recv_per_sec or 0.0) / 1024.0
        st.metric(
            label="🌐 Network I/O",
            value=f"TX {format_throughput(tx_kbps)}",
            delta=f"RX {format_throughput(rx_kbps)}",
            delta_color="off",
            help=f"Total TX: {format_bytes(metric.network_bytes_sent)} | Total RX: {format_bytes(metric.network_bytes_recv)}",
        )

    with col5:
        proc_count = metric.process_count or 0
        top_name = metric.top_process_name or "N/A"
        top_cpu = f"{metric.top_process_cpu_percent:.1f}%" if metric.top_process_cpu_percent is not None else "0%"
        st.metric(
            label="⚙️ Active Tasks",
            value=f"{proc_count} Procs",
            delta=f"Top: {top_name} ({top_cpu})",
            delta_color="off",
            help=f"Top resource consumer PID: {metric.top_process_pid or 'N/A'}",
        )
