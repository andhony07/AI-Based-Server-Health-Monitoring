"""Telemetry metric cards component."""

from __future__ import annotations

from typing import Any, Optional, Union

import streamlit as st

from app.dashboard.utils.formatting import (
    format_bytes,
    format_percent,
    format_throughput,
    get_resource_status,
)
from app.database.models import SystemMetricRecord
from app.dashboard.utils.theme import get_theme_tokens
from app.models.metrics import SystemMetrics


def adapt_telemetry_to_record(
    metric: Union[SystemMetricRecord, SystemMetrics, dict[str, Any], None],
) -> Optional[SystemMetricRecord]:
    """Adapt any telemetry representation (SystemMetrics, SystemMetricRecord, or dict) into a SystemMetricRecord.

    Args:
        metric: An instance of SystemMetricRecord, SystemMetrics, dictionary, or None.

    Returns:
        A SystemMetricRecord instance, or None if the input is None.
    """
    if metric is None:
        return None

    if isinstance(metric, SystemMetricRecord):
        return metric

    if isinstance(metric, SystemMetrics):
        top_p = max(metric.processes, key=lambda p: getattr(p, "cpu_percent", 0.0)) if metric.processes else None
        return SystemMetricRecord(
            id=0,
            timestamp=metric.timestamp,
            cpu_percent=metric.cpu.utilization_percent if metric.cpu is not None else None,
            cpu_logical_cores=metric.cpu.logical_cores if metric.cpu is not None else None,
            cpu_physical_cores=metric.cpu.physical_cores if metric.cpu is not None else None,
            memory_total_bytes=metric.memory.total_bytes if metric.memory is not None else None,
            memory_used_bytes=metric.memory.used_bytes if metric.memory is not None else None,
            memory_available_bytes=metric.memory.available_bytes if metric.memory is not None else None,
            memory_percent=metric.memory.utilization_percent if metric.memory is not None else None,
            disk_total_bytes=metric.disk.total_bytes if metric.disk is not None else None,
            disk_used_bytes=metric.disk.used_bytes if metric.disk is not None else None,
            disk_free_bytes=metric.disk.free_bytes if metric.disk is not None else None,
            disk_percent=metric.disk.utilization_percent if metric.disk is not None else None,
            network_bytes_sent=metric.network.bytes_sent if metric.network is not None else None,
            network_bytes_recv=metric.network.bytes_recv if metric.network is not None else None,
            network_bytes_sent_per_sec=metric.network.bytes_sent_per_sec if metric.network is not None else None,
            network_bytes_recv_per_sec=metric.network.bytes_recv_per_sec if metric.network is not None else None,
            process_count=len(metric.processes) if metric.processes is not None else None,
            top_process_pid=top_p.pid if top_p is not None else None,
            top_process_name=top_p.name if top_p is not None else None,
            top_process_cpu_percent=top_p.cpu_percent if top_p is not None else None,
            top_process_memory_percent=top_p.memory_percent if top_p is not None else None,
        )

    if isinstance(metric, dict):
        cpu_data = metric.get("cpu") if isinstance(metric.get("cpu"), dict) else {}
        mem_data = metric.get("memory") if isinstance(metric.get("memory"), dict) else {}
        disk_data = metric.get("disk") if isinstance(metric.get("disk"), dict) else {}
        net_data = metric.get("network") if isinstance(metric.get("network"), dict) else {}
        procs_data = metric.get("processes") if isinstance(metric.get("processes"), list) else []

        top_p_dict = max(procs_data, key=lambda p: p.get("cpu_percent", 0.0)) if procs_data else {}

        return SystemMetricRecord(
            id=int(metric.get("id", 0)),
            timestamp=metric.get("timestamp"),
            cpu_percent=metric.get("cpu_percent", cpu_data.get("utilization_percent")),
            cpu_logical_cores=metric.get("cpu_logical_cores", cpu_data.get("logical_cores")),
            cpu_physical_cores=metric.get("cpu_physical_cores", cpu_data.get("physical_cores")),
            memory_total_bytes=metric.get("memory_total_bytes", mem_data.get("total_bytes")),
            memory_used_bytes=metric.get("memory_used_bytes", mem_data.get("used_bytes")),
            memory_available_bytes=metric.get("memory_available_bytes", mem_data.get("available_bytes")),
            memory_percent=metric.get("memory_percent", mem_data.get("utilization_percent")),
            disk_total_bytes=metric.get("disk_total_bytes", disk_data.get("total_bytes")),
            disk_used_bytes=metric.get("disk_used_bytes", disk_data.get("used_bytes")),
            disk_free_bytes=metric.get("disk_free_bytes", disk_data.get("free_bytes")),
            disk_percent=metric.get("disk_percent", disk_data.get("utilization_percent")),
            network_bytes_sent=metric.get("network_bytes_sent", net_data.get("bytes_sent")),
            network_bytes_recv=metric.get("network_bytes_recv", net_data.get("bytes_recv")),
            network_bytes_sent_per_sec=metric.get("network_bytes_sent_per_sec", net_data.get("bytes_sent_per_sec")),
            network_bytes_recv_per_sec=metric.get("network_bytes_recv_per_sec", net_data.get("bytes_recv_per_sec")),
            process_count=metric.get("process_count", len(procs_data) if procs_data else None),
            top_process_pid=metric.get("top_process_pid", top_p_dict.get("pid")),
            top_process_name=metric.get("top_process_name", top_p_dict.get("name")),
            top_process_cpu_percent=metric.get("top_process_cpu_percent", top_p_dict.get("cpu_percent")),
            top_process_memory_percent=metric.get("top_process_memory_percent", top_p_dict.get("memory_percent")),
        )

    return None


def render_metric_cards(
    metric: Optional[Union[SystemMetricRecord, SystemMetrics, dict[str, Any]]],
    is_simulated: bool = False,
    theme: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Render executive metric cards for CPU, Memory, Disk, Network, and Processes.

    Supports both persisted SystemMetricRecord and in-memory SystemMetrics models.

    Args:
        metric: Most recent SystemMetricRecord, SystemMetrics, or None.
        is_simulated: Whether this telemetry represents a synthetic simulation.
        theme: Optional active theme ('dark' or 'light').
        **kwargs: Additional legacy or forward-compatible keyword arguments.
    """
    active_mode = theme or kwargs.get("theme")
    tokens = get_theme_tokens(active_mode)
    record = adapt_telemetry_to_record(metric)

    if record is None:
        st.warning("⚠️ No system telemetry records found in the database. Start monitoring or capture a snapshot below.")
        return

    if is_simulated:
        st.caption("🔬 Telemetry Source: **SIMULATED** (Deterministic synthetic telemetry frame)")

    # Status assessments (returns Nominal/Warning/Critical/Unknown)
    cpu_status, cpu_color, cpu_icon = get_resource_status(record.cpu_percent, warn_thresh=80.0, crit_thresh=95.0)
    ram_status, ram_color, ram_icon = get_resource_status(record.memory_percent, warn_thresh=85.0, crit_thresh=95.0)
    disk_status, disk_color, disk_icon = get_resource_status(record.disk_percent, warn_thresh=90.0, crit_thresh=95.0)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        cpu_val = format_percent(record.cpu_percent)
        cores_info = f"{record.cpu_logical_cores} Cores" if record.cpu_logical_cores is not None else "Cores: N/A"
        st.metric(
            label=f"{cpu_icon} CPU Load",
            value=cpu_val,
            delta=cores_info,
            delta_color="off",
            help=f"Status: {cpu_status}. Thresholds: Warning >80%, Critical >95%",
        )

    with col2:
        ram_val = format_percent(record.memory_percent)
        ram_used = format_bytes(record.memory_used_bytes)
        ram_total = format_bytes(record.memory_total_bytes)
        delta_ram = f"{ram_used} / {ram_total}" if (record.memory_used_bytes is not None or record.memory_total_bytes is not None) else "N/A"
        st.metric(
            label=f"{ram_icon} Memory (RAM)",
            value=ram_val,
            delta=delta_ram,
            delta_color="off",
            help=f"Status: {ram_status}. Thresholds: Warning >85%, Critical >95%",
        )

    with col3:
        disk_val = format_percent(record.disk_percent)
        disk_used = format_bytes(record.disk_used_bytes)
        disk_total = format_bytes(record.disk_total_bytes)
        delta_disk = f"{disk_used} / {disk_total}" if (record.disk_used_bytes is not None or record.disk_total_bytes is not None) else "N/A"
        st.metric(
            label=f"{disk_icon} Disk Storage",
            value=disk_val,
            delta=delta_disk,
            delta_color="off",
            help=f"Status: {disk_status}. Thresholds: Warning >90%, Critical >95%",
        )

    with col4:
        tx_kbps = (record.network_bytes_sent_per_sec / 1024.0) if record.network_bytes_sent_per_sec is not None else None
        rx_kbps = (record.network_bytes_recv_per_sec / 1024.0) if record.network_bytes_recv_per_sec is not None else None
        tx_str = format_throughput(tx_kbps)
        rx_str = format_throughput(rx_kbps)
        tx_tot = format_bytes(record.network_bytes_sent)
        rx_tot = format_bytes(record.network_bytes_recv)
        st.metric(
            label="🌐 Network I/O",
            value=f"TX {tx_str}",
            delta=f"RX {rx_str}",
            delta_color="off",
            help=f"Total TX: {tx_tot} | Total RX: {rx_tot}",
        )

    with col5:
        proc_str = f"{record.process_count} Procs" if record.process_count is not None else "N/A Procs"
        top_name = record.top_process_name if record.top_process_name else "N/A"
        top_cpu = f"{record.top_process_cpu_percent:.1f}%" if record.top_process_cpu_percent is not None else "N/A"
        top_pid_str = str(record.top_process_pid) if record.top_process_pid is not None else "N/A"
        st.metric(
            label="⚙️ Active Tasks",
            value=proc_str,
            delta=f"Top: {top_name} ({top_cpu})",
            delta_color="off",
            help=f"Top resource consumer PID: {top_pid_str}",
        )
