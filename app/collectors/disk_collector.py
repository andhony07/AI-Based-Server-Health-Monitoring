"""Disk storage telemetry metric collector.

Discovers accessible filesystem partitions, inspects storage capacities and usage,
handles platform-specific quirks (e.g., Windows drive letters and optical drives),
and skips inaccessible volumes gracefully.
"""

from __future__ import annotations
from typing import Optional

import psutil

from app.collectors.base import BaseCollector
from app.collectors.disk_activity import (
    BaseDiskActivityProvider,
    create_default_disk_activity_provider,
)
from app.models.metrics import DiskMetrics, DiskPartitionMetrics


class DiskCollector(BaseCollector[DiskMetrics]):
    """Collector for local filesystem storage capacity, utilization, and disk active time."""

    def __init__(
        self,
        include_all: bool = False,
        activity_provider: Optional[BaseDiskActivityProvider] = None,
    ) -> None:
        """Initialize the Disk collector.

        Args:
            include_all: Whether to inspect all virtual/virtualized partitions
                or only physical devices (defaults to False for physical only).
            activity_provider: Optional custom disk activity provider for testing or alternative platforms.
        """
        super().__init__(name="disk")
        self.include_all = include_all
        self.activity_provider: BaseDiskActivityProvider = (
            activity_provider or create_default_disk_activity_provider()
        )

    def collect(self) -> DiskMetrics:
        """Harvest disk partition usage metrics and physical disk active time.

        Returns:
            DiskMetrics containing partition metrics, aggregate storage, and disk active time.

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

        # Harvest physical disk activity and throughput
        activity = self.activity_provider.get_activity()

        return DiskMetrics(
            partitions=partition_metrics,
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            utilization_percent=agg_percent,
            active_time_percent=activity.active_time_percent,
            read_bytes_per_sec=activity.read_bytes_per_sec,
            write_bytes_per_sec=activity.write_bytes_per_sec,
        )

    def close(self) -> None:
        """Release underlying query handles in the activity provider."""
        self.activity_provider.close()
