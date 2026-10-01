"""CPU telemetry metric collector.

Collects real-time overall CPU utilization, per-core utilization, and core counts
using psutil with non-blocking or configurable sampling intervals.
"""

from __future__ import annotations

from typing import Optional

import psutil

from app.collectors.base import BaseCollector
from app.models.metrics import CPUMetrics


class CPUCollector(BaseCollector[CPUMetrics]):
    """Collector for host CPU metrics."""

    def __init__(self, sample_interval: Optional[float] = None) -> None:
        """Initialize the CPU collector.

        Args:
            sample_interval: Optional blocking interval (seconds) for psutil sampling.
                Defaults to None (non-blocking, calculating utilization since previous call).
        """
        super().__init__(name="cpu")
        self.sample_interval = sample_interval

        # Prime psutil's internal CPU time baselines so subsequent calls with interval=None
        # return meaningful utilization elapsed since this initialization.
        try:
            psutil.cpu_percent(interval=None)
            psutil.cpu_percent(percpu=True, interval=None)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("Failed to prime initial CPU counter baseline: %s", exc)

    def collect(self) -> CPUMetrics:
        """Harvest CPU telemetry metrics from host system.

        Returns:
            CPUMetrics containing overall utilization, logical/physical core counts,
            and per-core utilization percentages.

        Raises:
            RuntimeError: If CPU metrics cannot be retrieved from the OS.
        """
        try:
            utilization_percent = float(
                psutil.cpu_percent(interval=self.sample_interval)
            )
            per_core = [
                float(pct)
                for pct in psutil.cpu_percent(
                    percpu=True, interval=self.sample_interval
                )
            ]

            logical_cores = psutil.cpu_count(logical=True) or 1
            physical_cores = psutil.cpu_count(logical=False)

            return CPUMetrics(
                utilization_percent=utilization_percent,
                logical_cores=logical_cores,
                physical_cores=physical_cores,
                per_core_percent=per_core,
            )
        except Exception as exc:
            self.logger.error("Failed to collect CPU metrics: %s", exc)
            raise RuntimeError(f"CPU telemetry collection error: {exc}") from exc
