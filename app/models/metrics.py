"""Structured data models for system telemetry metrics.

Provides typed dataclasses for CPU, memory, disk, network, process,
and consolidated system metrics. Designed to be JSON-serializable and compatible
with future persistence (SQLite) and machine learning preprocessing pipelines.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class CPUMetrics:
    """CPU telemetry metrics.

    Attributes:
        utilization_percent: Overall CPU utilization percentage (0.0 - 100.0).
        logical_cores: Total logical CPU core count.
        physical_cores: Physical CPU core count, if detectable.
        per_core_percent: Utilization percentage for each individual core.
    """

    utilization_percent: float
    logical_cores: int
    physical_cores: Optional[int] = None
    per_core_percent: list[float] = field(default_factory=list)


# Backward-compatible casing alias
CpuMetrics = CPUMetrics


@dataclass(frozen=True)
class MemoryMetrics:
    """System memory (RAM) telemetry metrics.

    Attributes:
        total_bytes: Total physical RAM in bytes.
        available_bytes: Available RAM in bytes immediately allocatable to processes.
        used_bytes: Memory currently in use in bytes.
        utilization_percent: Memory utilization percentage (0.0 - 100.0).
    """

    total_bytes: int
    available_bytes: int
    used_bytes: int
    utilization_percent: float

    @property
    def total_mb(self) -> float:
        """Total memory in megabytes (MB)."""
        return round(self.total_bytes / (1024 * 1024), 2)

    @property
    def used_mb(self) -> float:
        """Used memory in megabytes (MB)."""
        return round(self.used_bytes / (1024 * 1024), 2)

    @property
    def available_mb(self) -> float:
        """Available memory in megabytes (MB)."""
        return round(self.available_bytes / (1024 * 1024), 2)


@dataclass(frozen=True)
class DiskPartitionMetrics:
    """Disk storage metrics for an individual filesystem partition or mount point.

    Attributes:
        mount_point: Drive or filesystem mount point (e.g., 'C:\\' or '/').
        total_bytes: Total storage capacity in bytes.
        used_bytes: Used storage capacity in bytes.
        free_bytes: Free storage capacity in bytes.
        utilization_percent: Storage usage percentage (0.0 - 100.0).
        device: Underlying block device or volume identifier, if available.
        fstype: Filesystem type (e.g., 'NTFS', 'FAT32', 'ext4'), if available.
    """

    mount_point: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    utilization_percent: float
    device: Optional[str] = None
    fstype: Optional[str] = None

    @property
    def total_gb(self) -> float:
        """Total storage in gigabytes (GB)."""
        return round(self.total_bytes / (1024**3), 2)

    @property
    def used_gb(self) -> float:
        """Used storage in gigabytes (GB)."""
        return round(self.used_bytes / (1024**3), 2)

    @property
    def free_gb(self) -> float:
        """Free storage in gigabytes (GB)."""
        return round(self.free_bytes / (1024**3), 2)


@dataclass(frozen=True)
class DiskMetrics:
    """Aggregated disk storage telemetry across all accessible partitions.

    Attributes:
        partitions: List of metrics for each detected accessible partition.
        total_bytes: Sum of storage capacity across all measured partitions.
        used_bytes: Sum of used storage capacity across all measured partitions.
        free_bytes: Sum of free storage capacity across all measured partitions.
        utilization_percent: Aggregated storage utilization percentage.
    """

    partitions: list[DiskPartitionMetrics] = field(default_factory=list)
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    utilization_percent: float = 0.0


@dataclass(frozen=True)
class NetworkMetrics:
    """Network I/O traffic and throughput telemetry metrics.

    Attributes:
        bytes_sent: Cumulative total bytes transmitted since system startup.
        bytes_recv: Cumulative total bytes received since system startup.
        packets_sent: Cumulative packets transmitted.
        packets_recv: Cumulative packets received.
        bytes_sent_per_sec: Upload throughput in bytes per second.
        bytes_recv_per_sec: Download throughput in bytes per second.
    """

    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    bytes_sent_per_sec: float = 0.0
    bytes_recv_per_sec: float = 0.0

    @property
    def upload_kbps(self) -> float:
        """Upload throughput in kilobytes per second (KB/s)."""
        return round(self.bytes_sent_per_sec / 1024.0, 2)

    @property
    def download_kbps(self) -> float:
        """Download throughput in kilobytes per second (KB/s)."""
        return round(self.bytes_recv_per_sec / 1024.0, 2)


@dataclass(frozen=True)
class ProcessMetrics:
    """Process execution and resource utilization snapshot.

    Attributes:
        pid: Unique Operating System process identifier.
        name: Name of the process executable.
        cpu_percent: Process CPU utilization percentage.
        memory_percent: Process physical memory percentage.
        status: Current process status (e.g., 'running', 'sleeping', 'idle').
    """

    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str


@dataclass(frozen=True)
class SystemMetrics:
    """Consolidated system telemetry snapshot capturing all metric domains.

    Attributes:
        timestamp: Time of metric acquisition (UTC timezone aware).
        cpu: CPU telemetry metrics, if successfully collected.
        memory: Memory telemetry metrics, if successfully collected.
        disk: Disk telemetry metrics, if successfully collected.
        network: Network telemetry metrics, if successfully collected.
        processes: List of top monitored processes.
        errors: List of error messages captured during partial collection failures.
    """

    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    cpu: Optional[CPUMetrics] = None
    memory: Optional[MemoryMetrics] = None
    disk: Optional[DiskMetrics] = None
    network: Optional[NetworkMetrics] = None
    processes: list[ProcessMetrics] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to a JSON-compatible dictionary.

        Returns:
            Dictionary containing primitive types with ISO 8601 formatted timestamp.
        """
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data
