"""Data cleaning and sanitization subsystem for telemetry metrics.

Handles missing metric domains, non-finite values (NaN, inf), clamping out-of-bounds
percentages, and generating quality indicator flags without log flooding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.core.logging_config import get_logger
from app.models.metrics import SystemMetrics
from app.preprocessing.validator import ValidationResult


@dataclass(frozen=True)
class CleanedSystemMetrics:
    """Sanitized, standardized representation of system telemetry metrics.

    Attributes:
        timestamp: Time of telemetry sample.
        cpu_percent: Sanitized CPU utilization percentage (0.0 - 100.0).
        logical_cores: Logical core count (>= 1).
        per_core_percent: List of sanitized per-core utilization percentages.
        memory_percent: Sanitized physical memory utilization percentage (0.0 - 100.0).
        memory_total_mb: Total physical memory in MB.
        memory_used_mb: Used physical memory in MB.
        memory_available_mb: Available physical memory in MB.
        disk_percent: Sanitized aggregate disk utilization percentage (0.0 - 100.0).
        disk_total_gb: Aggregate disk capacity in GB.
        disk_used_gb: Aggregate used disk space in GB.
        disk_free_gb: Aggregate free disk space in GB.
        network_sent_bytes_per_sec: Upload throughput in bytes per second.
        network_recv_bytes_per_sec: Download throughput in bytes per second.
        process_count: Total monitored running processes.
        top_process_cpu_percent: Highest individual process CPU utilization %.
        top_process_memory_percent: Highest individual process memory utilization %.
        top_processes_total_cpu_percent: Sum of CPU utilization across monitored processes.
        top_processes_total_memory_percent: Sum of memory utilization across monitored processes.
        is_cpu_missing: 1.0 if CPU domain was unavailable, else 0.0.
        is_memory_missing: 1.0 if memory domain was unavailable, else 0.0.
        is_disk_missing: 1.0 if disk domain was unavailable, else 0.0.
        is_network_missing: 1.0 if network domain was unavailable, else 0.0.
        is_processes_missing: 1.0 if processes domain was unavailable, else 0.0.
    """

    timestamp: datetime
    # CPU
    cpu_percent: float
    logical_cores: int
    per_core_percent: list[float] = field(default_factory=list)
    # Memory
    memory_percent: float = 0.0
    memory_total_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    # Disk
    disk_percent: float = 0.0
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    # Network
    network_sent_bytes_per_sec: float = 0.0
    network_recv_bytes_per_sec: float = 0.0
    # Processes
    process_count: int = 0
    top_process_cpu_percent: float = 0.0
    top_process_memory_percent: float = 0.0
    top_processes_total_cpu_percent: float = 0.0
    top_processes_total_memory_percent: float = 0.0
    # Quality / Missing Indicators
    is_cpu_missing: float = 0.0
    is_memory_missing: float = 0.0
    is_disk_missing: float = 0.0
    is_network_missing: float = 0.0
    is_processes_missing: float = 0.0


class MetricsCleaner:
    """Sanitizes raw SystemMetrics and provides safe imputation for missing or corrupted data."""

    def __init__(self, missing_value_strategy: str = "zero") -> None:
        """Initialize cleaner with configured missing data strategy.

        Args:
            missing_value_strategy: Strategy for imputing unavailable metrics
                ('zero', 'indicator', 'last_valid').
        """
        self.strategy = missing_value_strategy.lower().strip()
        self.logger = get_logger("app.preprocessing.cleaner")
        self._last_valid_metrics: Optional[CleanedSystemMetrics] = None
        self._warned_issues: set[str] = set()

    def clean(
        self, metrics: SystemMetrics, validation: ValidationResult
    ) -> CleanedSystemMetrics:
        """Sanitize incoming telemetry snapshot and return CleanedSystemMetrics.

        Args:
            metrics: Raw SystemMetrics snapshot.
            validation: ValidationResult produced by MetricsValidator.

        Returns:
            CleanedSystemMetrics with bounded numbers and indicator flags.
        """
        # Log unique validation issues without spamming
        for issue in validation.issues:
            issue_key = f"{issue.domain}:{issue.field_name}:{issue.issue_type}"
            if issue_key not in self._warned_issues:
                self.logger.warning(
                    "Data validation [%s]: %s (value=%s)",
                    issue.domain.upper(),
                    issue.message,
                    issue.value,
                )
                self._warned_issues.add(issue_key)

        timestamp = getattr(metrics, "timestamp", datetime.now())

        # Clean CPU
        is_cpu_missing = 1.0 if metrics.cpu is None else 0.0
        if metrics.cpu is not None:
            cpu_percent = self._sanitize_percentage(metrics.cpu.utilization_percent)
            logical_cores = max(1, metrics.cpu.logical_cores)
            per_core = [
                self._sanitize_percentage(c) for c in metrics.cpu.per_core_percent
            ]
        elif self.strategy == "last_valid" and self._last_valid_metrics is not None:
            cpu_percent = self._last_valid_metrics.cpu_percent
            logical_cores = self._last_valid_metrics.logical_cores
            per_core = list(self._last_valid_metrics.per_core_percent)
        else:
            cpu_percent = 0.0
            logical_cores = 1
            per_core = []

        # Clean Memory
        is_mem_missing = 1.0 if metrics.memory is None else 0.0
        if metrics.memory is not None:
            mem_percent = self._sanitize_percentage(metrics.memory.utilization_percent)
            mem_total_mb = self._sanitize_non_negative(metrics.memory.total_mb)
            mem_used_mb = self._sanitize_non_negative(metrics.memory.used_mb)
            mem_avail_mb = self._sanitize_non_negative(metrics.memory.available_mb)
        elif self.strategy == "last_valid" and self._last_valid_metrics is not None:
            mem_percent = self._last_valid_metrics.memory_percent
            mem_total_mb = self._last_valid_metrics.memory_total_mb
            mem_used_mb = self._last_valid_metrics.memory_used_mb
            mem_avail_mb = self._last_valid_metrics.memory_available_mb
        else:
            mem_percent = 0.0
            mem_total_mb = 0.0
            mem_used_mb = 0.0
            mem_avail_mb = 0.0

        # Clean Disk
        is_disk_missing = 1.0 if metrics.disk is None else 0.0
        if metrics.disk is not None:
            disk_percent = self._sanitize_percentage(metrics.disk.utilization_percent)
            disk_total_gb = self._sanitize_non_negative(
                round(metrics.disk.total_bytes / (1024**3), 2)
            )
            disk_used_gb = self._sanitize_non_negative(
                round(metrics.disk.used_bytes / (1024**3), 2)
            )
            disk_free_gb = self._sanitize_non_negative(
                round(metrics.disk.free_bytes / (1024**3), 2)
            )
        elif self.strategy == "last_valid" and self._last_valid_metrics is not None:
            disk_percent = self._last_valid_metrics.disk_percent
            disk_total_gb = self._last_valid_metrics.disk_total_gb
            disk_used_gb = self._last_valid_metrics.disk_used_gb
            disk_free_gb = self._last_valid_metrics.disk_free_gb
        else:
            disk_percent = 0.0
            disk_total_gb = 0.0
            disk_used_gb = 0.0
            disk_free_gb = 0.0

        # Clean Network
        is_net_missing = 1.0 if metrics.network is None else 0.0
        if metrics.network is not None:
            net_sent_rate = self._sanitize_non_negative(metrics.network.bytes_sent_per_sec)
            net_recv_rate = self._sanitize_non_negative(metrics.network.bytes_recv_per_sec)
        elif self.strategy == "last_valid" and self._last_valid_metrics is not None:
            net_sent_rate = self._last_valid_metrics.network_sent_bytes_per_sec
            net_recv_rate = self._last_valid_metrics.network_recv_bytes_per_sec
        else:
            net_sent_rate = 0.0
            net_recv_rate = 0.0

        # Clean Processes
        is_proc_missing = 1.0 if metrics.processes is None else 0.0
        proc_list = metrics.processes or []
        process_count = len(proc_list)
        if proc_list:
            top_proc_cpu = self._sanitize_non_negative(
                max((p.cpu_percent for p in proc_list if hasattr(p, "cpu_percent")), default=0.0)
            )
            top_proc_mem = self._sanitize_percentage(
                max((p.memory_percent for p in proc_list if hasattr(p, "memory_percent")), default=0.0)
            )
            total_proc_cpu = self._sanitize_non_negative(
                sum((p.cpu_percent for p in proc_list if hasattr(p, "cpu_percent")))
            )
            total_proc_mem = self._sanitize_non_negative(
                sum((p.memory_percent for p in proc_list if hasattr(p, "memory_percent")))
            )
        else:
            top_proc_cpu = 0.0
            top_proc_mem = 0.0
            total_proc_cpu = 0.0
            total_proc_mem = 0.0

        cleaned = CleanedSystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            logical_cores=logical_cores,
            per_core_percent=per_core,
            memory_percent=mem_percent,
            memory_total_mb=mem_total_mb,
            memory_used_mb=mem_used_mb,
            memory_available_mb=mem_avail_mb,
            disk_percent=disk_percent,
            disk_total_gb=disk_total_gb,
            disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb,
            network_sent_bytes_per_sec=net_sent_rate,
            network_recv_bytes_per_sec=net_recv_rate,
            process_count=process_count,
            top_process_cpu_percent=top_proc_cpu,
            top_process_memory_percent=top_proc_mem,
            top_processes_total_cpu_percent=total_proc_cpu,
            top_processes_total_memory_percent=total_proc_mem,
            is_cpu_missing=is_cpu_missing,
            is_memory_missing=is_mem_missing,
            is_disk_missing=is_disk_missing,
            is_network_missing=is_net_missing,
            is_processes_missing=is_proc_missing,
        )

        # Cache as last valid if at least one core metric was valid
        if not (is_cpu_missing and is_mem_missing and is_disk_missing):
            self._last_valid_metrics = cleaned

        return cleaned

    def _sanitize_percentage(self, val: Any) -> float:
        """Clamp numeric percentage to finite range [0.0, 100.0]."""
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            return 0.0
        return max(0.0, min(100.0, float(val)))

    def _sanitize_non_negative(self, val: Any) -> float:
        """Ensure numeric value is finite and >= 0.0."""
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            return 0.0
        return max(0.0, float(val))
