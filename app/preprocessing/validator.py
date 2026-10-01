"""Data validation subsystem for raw telemetry metrics.

Inspects incoming SystemMetrics snapshots for missing, invalid, negative,
out-of-range, and non-finite (NaN, inf) values while isolating domain failures
so valid metrics remain usable by downstream components.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)


@dataclass(frozen=True)
class ValidationIssue:
    """Represents an individual metric anomaly or schema validation issue.

    Attributes:
        domain: Telemetry domain (e.g., 'cpu', 'memory', 'disk', 'network', 'process').
        field_name: The metric attribute name experiencing an issue.
        issue_type: Category of issue ('missing', 'out_of_range', 'non_finite', 'invalid_type').
        message: Human-readable diagnostic description of the validation failure.
        value: The offending value, if any.
        severity: Severity level ('warning' or 'error').
    """

    domain: str
    field_name: str
    issue_type: str
    message: str
    value: Any = None
    severity: str = "warning"


@dataclass(frozen=True)
class ValidationResult:
    """Summary of metric validation across all telemetry domains.

    Attributes:
        is_valid: True if metrics passed validation without fatal structural errors.
        issues: List of ValidationIssue records captured during inspection.
    """

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """True if any validation issues were detected."""
        return len(self.issues) > 0

    @property
    def has_errors(self) -> bool:
        """True if any error-level validation issues occurred."""
        return any(issue.severity == "error" for issue in self.issues)

    def get_issues_for_domain(self, domain: str) -> list[ValidationIssue]:
        """Return all issues associated with a specific domain."""
        return [i for i in self.issues if i.domain == domain]


class MetricsValidator:
    """Validates raw SystemMetrics objects for operational constraints and mathematical validity."""

    def __init__(self) -> None:
        """Initialize the metrics validator."""

    def validate(self, metrics: Any) -> ValidationResult:
        """Inspect a SystemMetrics snapshot and return validation results.

        Args:
            metrics: The telemetry object to validate.

        Returns:
            ValidationResult with detailed issue records.
        """
        issues: list[ValidationIssue] = []

        if not isinstance(metrics, SystemMetrics):
            issues.append(
                ValidationIssue(
                    domain="system",
                    field_name="metrics",
                    issue_type="invalid_type",
                    message=f"Expected SystemMetrics instance, got {type(metrics).__name__}",
                    value=metrics,
                    severity="error",
                )
            )
            return ValidationResult(is_valid=False, issues=issues)

        # Validate timestamp
        self._validate_timestamp(metrics.timestamp, issues)

        # Validate CPU domain
        if metrics.cpu is None:
            issues.append(
                ValidationIssue(
                    domain="cpu",
                    field_name="cpu",
                    issue_type="missing",
                    message="CPU telemetry domain is missing or unavailable",
                    severity="warning",
                )
            )
        else:
            self._validate_cpu(metrics.cpu, issues)

        # Validate Memory domain
        if metrics.memory is None:
            issues.append(
                ValidationIssue(
                    domain="memory",
                    field_name="memory",
                    issue_type="missing",
                    message="Memory telemetry domain is missing or unavailable",
                    severity="warning",
                )
            )
        else:
            self._validate_memory(metrics.memory, issues)

        # Validate Disk domain
        if metrics.disk is None:
            issues.append(
                ValidationIssue(
                    domain="disk",
                    field_name="disk",
                    issue_type="missing",
                    message="Disk telemetry domain is missing or unavailable",
                    severity="warning",
                )
            )
        else:
            self._validate_disk(metrics.disk, issues)

        # Validate Network domain
        if metrics.network is None:
            issues.append(
                ValidationIssue(
                    domain="network",
                    field_name="network",
                    issue_type="missing",
                    message="Network telemetry domain is missing or unavailable",
                    severity="warning",
                )
            )
        else:
            self._validate_network(metrics.network, issues)

        # Validate Processes domain
        if not metrics.processes and metrics.processes is not None:
            # Empty process list is permissible, but validate if entries exist
            pass
        elif metrics.processes is None:
            issues.append(
                ValidationIssue(
                    domain="process",
                    field_name="processes",
                    issue_type="missing",
                    message="Process list is null or unavailable",
                    severity="warning",
                )
            )
        else:
            self._validate_processes(metrics.processes, issues)

        # If any errors exist, is_valid is False
        has_fatal_errors = any(i.severity == "error" for i in issues)
        return ValidationResult(is_valid=not has_fatal_errors, issues=issues)

    def _validate_timestamp(
        self, timestamp: Any, issues: list[ValidationIssue]
    ) -> None:
        """Validate timestamp validity."""
        if not isinstance(timestamp, datetime):
            issues.append(
                ValidationIssue(
                    domain="system",
                    field_name="timestamp",
                    issue_type="invalid_type",
                    message=f"Timestamp must be a datetime object, got {type(timestamp).__name__}",
                    value=timestamp,
                    severity="error",
                )
            )
            return

        now = datetime.now(timezone.utc)
        ts_utc = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
        delta_seconds = (ts_utc - now).total_seconds()
        # Disallow timestamps in the far future (> 1 day ahead)
        if delta_seconds > 86400:
            issues.append(
                ValidationIssue(
                    domain="system",
                    field_name="timestamp",
                    issue_type="out_of_range",
                    message=f"Timestamp is significantly in the future: {timestamp}",
                    value=timestamp,
                    severity="warning",
                )
            )

    def _validate_cpu(self, cpu: CPUMetrics, issues: list[ValidationIssue]) -> None:
        """Validate CPU metrics values."""
        self._check_float_range(
            "cpu", "utilization_percent", cpu.utilization_percent, 0.0, 100.0, issues
        )
        if not isinstance(cpu.logical_cores, int) or cpu.logical_cores <= 0:
            issues.append(
                ValidationIssue(
                    domain="cpu",
                    field_name="logical_cores",
                    issue_type="out_of_range",
                    message=f"Logical cores must be a positive integer, got: {cpu.logical_cores}",
                    value=cpu.logical_cores,
                    severity="warning",
                )
            )
        if cpu.physical_cores is not None:
            if not isinstance(cpu.physical_cores, int) or cpu.physical_cores <= 0:
                issues.append(
                    ValidationIssue(
                        domain="cpu",
                        field_name="physical_cores",
                        issue_type="out_of_range",
                        message=f"Physical cores must be positive, got: {cpu.physical_cores}",
                        value=cpu.physical_cores,
                        severity="warning",
                    )
                )

        if isinstance(cpu.per_core_percent, list):
            for idx, core_pct in enumerate(cpu.per_core_percent):
                self._check_float_range(
                    "cpu", f"per_core_percent[{idx}]", core_pct, 0.0, 100.0, issues
                )

    def _validate_memory(
        self, mem: MemoryMetrics, issues: list[ValidationIssue]
    ) -> None:
        """Validate virtual memory metrics."""
        self._check_float_range(
            "memory", "utilization_percent", mem.utilization_percent, 0.0, 100.0, issues
        )
        if not isinstance(mem.total_bytes, (int, float)) or mem.total_bytes <= 0:
            issues.append(
                ValidationIssue(
                    domain="memory",
                    field_name="total_bytes",
                    issue_type="out_of_range",
                    message=f"Total memory bytes must be positive, got: {mem.total_bytes}",
                    value=mem.total_bytes,
                    severity="warning",
                )
            )
        if not isinstance(mem.available_bytes, (int, float)) or mem.available_bytes < 0:
            issues.append(
                ValidationIssue(
                    domain="memory",
                    field_name="available_bytes",
                    issue_type="out_of_range",
                    message=f"Available memory bytes cannot be negative, got: {mem.available_bytes}",
                    value=mem.available_bytes,
                    severity="warning",
                )
            )
        if not isinstance(mem.used_bytes, (int, float)) or mem.used_bytes < 0:
            issues.append(
                ValidationIssue(
                    domain="memory",
                    field_name="used_bytes",
                    issue_type="out_of_range",
                    message=f"Used memory bytes cannot be negative, got: {mem.used_bytes}",
                    value=mem.used_bytes,
                    severity="warning",
                )
            )

    def _validate_disk(
        self, disk: DiskMetrics, issues: list[ValidationIssue]
    ) -> None:
        """Validate disk storage metrics."""
        self._check_float_range(
            "disk", "utilization_percent", disk.utilization_percent, 0.0, 100.0, issues
        )
        if disk.total_bytes < 0 or disk.used_bytes < 0 or disk.free_bytes < 0:
            issues.append(
                ValidationIssue(
                    domain="disk",
                    field_name="capacities",
                    issue_type="out_of_range",
                    message="Disk capacity values cannot be negative",
                    severity="warning",
                )
            )

    def _validate_network(
        self, net: NetworkMetrics, issues: list[ValidationIssue]
    ) -> None:
        """Validate network traffic and rate metrics."""
        for field_name in ["bytes_sent", "bytes_recv", "packets_sent", "packets_recv"]:
            val = getattr(net, field_name, None)
            if not isinstance(val, (int, float)) or val < 0:
                issues.append(
                    ValidationIssue(
                        domain="network",
                        field_name=field_name,
                        issue_type="out_of_range",
                        message=f"Network counter '{field_name}' must be non-negative, got: {val}",
                        value=val,
                        severity="warning",
                    )
                )

        for rate_name in ["bytes_sent_per_sec", "bytes_recv_per_sec"]:
            val = getattr(net, rate_name, None)
            self._check_non_negative_finite("network", rate_name, val, issues)

    def _validate_processes(
        self, processes: list[ProcessMetrics], issues: list[ValidationIssue]
    ) -> None:
        """Validate individual monitored processes."""
        for idx, proc in enumerate(processes):
            if not isinstance(proc, ProcessMetrics):
                issues.append(
                    ValidationIssue(
                        domain="process",
                        field_name=f"processes[{idx}]",
                        issue_type="invalid_type",
                        message=f"Expected ProcessMetrics object, got {type(proc).__name__}",
                        value=proc,
                        severity="warning",
                    )
                )
                continue

            self._check_non_negative_finite(
                "process", f"process[{proc.pid}].cpu_percent", proc.cpu_percent, issues
            )
            self._check_float_range(
                "process",
                f"process[{proc.pid}].memory_percent",
                proc.memory_percent,
                0.0,
                100.0,
                issues,
            )

    def _check_float_range(
        self,
        domain: str,
        field_name: str,
        val: Any,
        min_val: float,
        max_val: float,
        issues: list[ValidationIssue],
    ) -> None:
        """Check that a numeric value is finite and within expected range [min_val, max_val]."""
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            issues.append(
                ValidationIssue(
                    domain=domain,
                    field_name=field_name,
                    issue_type="non_finite",
                    message=f"Field '{field_name}' contains non-finite or invalid number: {val}",
                    value=val,
                    severity="warning",
                )
            )
            return

        if val < min_val or val > max_val:
            issues.append(
                ValidationIssue(
                    domain=domain,
                    field_name=field_name,
                    issue_type="out_of_range",
                    message=f"Field '{field_name}' out of range [{min_val}, {max_val}]: {val}",
                    value=val,
                    severity="warning",
                )
            )

    def _check_non_negative_finite(
        self,
        domain: str,
        field_name: str,
        val: Any,
        issues: list[ValidationIssue],
    ) -> None:
        """Check that a numeric value is finite and non-negative."""
        if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
            issues.append(
                ValidationIssue(
                    domain=domain,
                    field_name=field_name,
                    issue_type="non_finite",
                    message=f"Field '{field_name}' contains non-finite or invalid number: {val}",
                    value=val,
                    severity="warning",
                )
            )
            return

        if val < 0.0:
            issues.append(
                ValidationIssue(
                    domain=domain,
                    field_name=field_name,
                    issue_type="out_of_range",
                    message=f"Field '{field_name}' cannot be negative: {val}",
                    value=val,
                    severity="warning",
                )
            )
