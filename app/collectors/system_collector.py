"""Central telemetry coordination and system metrics collection engine.

Integrates individual CPU, memory, disk, network, and process collectors into
a unified, failure-isolated telemetry pipeline supporting single-shot and periodic sampling.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from app.collectors.base import BaseCollector
from app.collectors.cpu_collector import CPUCollector
from app.collectors.disk_collector import DiskCollector
from app.collectors.memory_collector import MemoryCollector
from app.collectors.network_collector import NetworkCollector
from app.collectors.process_collector import ProcessCollector
from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)


class SystemCollector(BaseCollector[SystemMetrics]):
    """Orchestrates individual telemetry collectors and manages metric aggregation."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        cpu_collector: Optional[CPUCollector] = None,
        memory_collector: Optional[MemoryCollector] = None,
        disk_collector: Optional[DiskCollector] = None,
        network_collector: Optional[NetworkCollector] = None,
        process_collector: Optional[ProcessCollector] = None,
    ) -> None:
        """Initialize SystemCollector with individual domain collectors.

        Args:
            settings: Application settings container. Defaults to active configuration.
            cpu_collector: Optional custom or mock CPU collector.
            memory_collector: Optional custom or mock Memory collector.
            disk_collector: Optional custom or mock Disk collector.
            network_collector: Optional custom or mock Network collector.
            process_collector: Optional custom or mock Process collector.
        """
        super().__init__(name="system")
        self.settings: Settings = settings or get_settings()

        # Initialize sub-collectors, reusing provided instances or instantiating defaults
        cpu_sample_interval = getattr(self.settings, "cpu_sample_interval", None)
        max_processes = getattr(self.settings, "max_processes", 10)

        self.cpu_collector = cpu_collector or CPUCollector(
            sample_interval=cpu_sample_interval
        )
        self.memory_collector = memory_collector or MemoryCollector()
        self.disk_collector = disk_collector or DiskCollector()
        self.network_collector = network_collector or NetworkCollector()
        self.process_collector = process_collector or ProcessCollector(
            max_processes=max_processes
        )

        self._stop_event = threading.Event()
        self.logger.info("SystemCollector initialized with all subsystem collectors.")

    def collect(self) -> SystemMetrics:
        """Harvest system metrics across all collectors with isolated failure boundaries.

        Returns:
            Unified SystemMetrics snapshot containing metrics and any isolated errors.
        """
        timestamp = datetime.now(timezone.utc)
        errors: list[str] = []

        cpu_metrics: Optional[CPUMetrics] = None
        try:
            cpu_metrics = self.cpu_collector.collect()
        except Exception as exc:
            msg = f"CPU collection error: {exc}"
            self.logger.warning(msg)
            errors.append(msg)

        memory_metrics: Optional[MemoryMetrics] = None
        try:
            memory_metrics = self.memory_collector.collect()
        except Exception as exc:
            msg = f"Memory collection error: {exc}"
            self.logger.warning(msg)
            errors.append(msg)

        disk_metrics: Optional[DiskMetrics] = None
        try:
            disk_metrics = self.disk_collector.collect()
        except Exception as exc:
            msg = f"Disk collection error: {exc}"
            self.logger.warning(msg)
            errors.append(msg)

        network_metrics: Optional[NetworkMetrics] = None
        try:
            network_metrics = self.network_collector.collect()
        except Exception as exc:
            msg = f"Network collection error: {exc}"
            self.logger.warning(msg)
            errors.append(msg)

        process_metrics: list[ProcessMetrics] = []
        try:
            process_metrics = self.process_collector.collect()
        except Exception as exc:
            msg = f"Process collection error: {exc}"
            self.logger.warning(msg)
            errors.append(msg)

        return SystemMetrics(
            timestamp=timestamp,
            cpu=cpu_metrics,
            memory=memory_metrics,
            disk=disk_metrics,
            network=network_metrics,
            processes=process_metrics,
            errors=errors,
        )

    def run_collection_loop(
        self,
        interval: Optional[float] = None,
        callback: Optional[Callable[[SystemMetrics], None]] = None,
        stop_event: Optional[threading.Event] = None,
        max_iterations: Optional[int] = None,
    ) -> list[SystemMetrics]:
        """Execute a periodic metric collection loop with graceful shutdown support.

        Args:
            interval: Collection interval in seconds. Defaults to settings.metric_collection_interval.
            callback: Optional hook called with each harvested SystemMetrics snapshot.
            stop_event: Optional threading.Event to signal termination.
            max_iterations: Optional maximum cycles to run before returning (useful for tests).

        Returns:
            List of collected SystemMetrics instances during this loop.
        """
        sampling_interval = (
            interval
            if interval is not None
            else self.settings.metric_collection_interval
        )
        active_stop_event = stop_event or self._stop_event
        collected_records: list[SystemMetrics] = []
        iteration = 0

        self.logger.info(
            "Starting metric collection loop (interval: %.2fs, max_iterations: %s)",
            sampling_interval,
            max_iterations if max_iterations is not None else "infinite",
        )

        try:
            while not active_stop_event.is_set():
                metrics = self.collect()
                collected_records.append(metrics)
                iteration += 1

                if callback is not None:
                    try:
                        callback(metrics)
                    except Exception as cb_err:
                        self.logger.error("Error in metric callback handler: %s", cb_err)

                if max_iterations is not None and iteration >= max_iterations:
                    self.logger.info(
                        "Reached maximum requested iterations (%d); terminating loop.",
                        max_iterations,
                    )
                    break

                # Sleep efficiently while remaining responsive to shutdown events
                if active_stop_event.wait(timeout=sampling_interval):
                    break

        except KeyboardInterrupt:
            self.logger.info("Collection loop interrupted by operator.")
        finally:
            self.logger.info(
                "Metric collection loop terminated. Completed %d sampling iterations.",
                iteration,
            )

        return collected_records

    def stop(self) -> None:
        """Signal the periodic collection loop to cleanly shut down."""
        self._stop_event.set()
