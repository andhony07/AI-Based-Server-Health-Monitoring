"""Disk storage telemetry metric collector.

Discovers accessible filesystem partitions, inspects storage capacities and usage,
handles platform-specific quirks (e.g., Windows drive letters and optical drives),
and skips inaccessible volumes gracefully.
"""

from __future__ import annotations

import psutil

from app.collectors.base import BaseCollector
from app.models.metrics import DiskMetrics, DiskPartitionMetrics


class DiskCollector(BaseCollector[DiskMetrics]):
    """Collector for local filesystem storage capacity and utilization."""

    def __init__(self, include_all: bool = False) -> None:
        """Initialize the Disk collector.

        Args:
            include_all: Whether to inspect all virtual/virtualized partitions
                or only physical devices (defaults to False for physical only).
        """
        super().__init__(name="disk")
        self.include_all = include_all

    def collect(self) -> DiskMetrics:
        """Harvest disk partition usage metrics across accessible local drives.

        Returns:
            DiskMetrics containing individual partition metrics and aggregated totals.

        Raises:
            RuntimeError: If partition enumeration completely fails.
        """
        try:
            partitions_raw = psutil.disk_partitions(all=self.include_all)
        except Exception as exc:
            self.logger.error("Failed to query disk partitions: %s", exc)
            raise RuntimeError(f"Disk partition enumeration failed: {exc}") from exc

        partition_metrics: list[DiskPartitionMetrics] = []
        seen_mounts: set[str] = set()

        for part in partitions_raw:
            mount = part.mountpoint
            # Normalize mount point representation to avoid duplicate listings
            norm_mount = mount.strip().rstrip("\\/").lower()
            if norm_mount in seen_mounts:
                continue
            seen_mounts.add(norm_mount)

            try:
                usage = psutil.disk_usage(mount)
                partition_metrics.append(
                    DiskPartitionMetrics(
                        mount_point=mount,
                        total_bytes=int(usage.total),
                        used_bytes=int(usage.used),
                        free_bytes=int(usage.free),
                        utilization_percent=float(usage.percent),
                        device=part.device,
                        fstype=part.fstype,
                    )
                )
            except (PermissionError, OSError, psutil.Error) as err:
                self.logger.debug(
                    "Skipping inaccessible partition '%s' (%s): %s",
                    mount,
                    part.device,
                    err,
                )
                continue

        total_bytes = sum(p.total_bytes for p in partition_metrics)
        used_bytes = sum(p.used_bytes for p in partition_metrics)
        free_bytes = sum(p.free_bytes for p in partition_metrics)
        agg_percent = (
            round((used_bytes / total_bytes * 100.0), 2)
            if total_bytes > 0
            else 0.0
        )

        return DiskMetrics(
            partitions=partition_metrics,
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            utilization_percent=agg_percent,
        )
