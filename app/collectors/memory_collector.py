"""Memory (RAM) telemetry metric collector.

Collects real-time physical memory metrics including total, available, used,
and utilization percentages using psutil.
"""

from __future__ import annotations

import psutil

from app.collectors.base import BaseCollector
from app.models.metrics import MemoryMetrics


class MemoryCollector(BaseCollector[MemoryMetrics]):
    """Collector for host virtual memory (RAM) metrics."""

    def __init__(self) -> None:
        """Initialize the Memory collector."""
        super().__init__(name="memory")

    def collect(self) -> MemoryMetrics:
        """Harvest virtual memory metrics from host system.

        Returns:
            MemoryMetrics containing total, available, used bytes, and utilization percentage.

        Raises:
            RuntimeError: If memory telemetry cannot be queried.
        """
        try:
            vm = psutil.virtual_memory()

            total_bytes = int(vm.total)
            available_bytes = int(vm.available)
            used_bytes = int(vm.used)
            utilization_percent = float(vm.percent)

            return MemoryMetrics(
                total_bytes=total_bytes,
                available_bytes=available_bytes,
                used_bytes=used_bytes,
                utilization_percent=utilization_percent,
            )
        except Exception as exc:
            self.logger.error("Failed to collect memory metrics: %s", exc)
            raise RuntimeError(f"Memory telemetry collection error: {exc}") from exc
