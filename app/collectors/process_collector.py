"""Process execution and resource utilization metric collector.

Collects running process metadata (PID, name, CPU %, memory %, status) using psutil.
Safely handles permission issues, terminated processes, and filters to the top resource consumers.
"""

from __future__ import annotations

import psutil

from app.collectors.base import BaseCollector
from app.models.metrics import ProcessMetrics


class ProcessCollector(BaseCollector[list[ProcessMetrics]]):
    """Collector for top resource-consuming host operating system processes."""

    def __init__(self, max_processes: int = 10) -> None:
        """Initialize the Process collector.

        Args:
            max_processes: Maximum number of top processes to return (must be > 0).
        """
        super().__init__(name="process")
        self.max_processes = max(1, max_processes)

    def collect(self) -> list[ProcessMetrics]:
        """Harvest process snapshots and return the top resource consumers.

        Returns:
            List of ProcessMetrics sorted by CPU utilization descending, limited
            to max_processes.

        Raises:
            RuntimeError: If process table enumeration completely fails.
        """
        processes: list[ProcessMetrics] = []

        try:
            # Query only necessary attributes to maximize collection performance
            # and minimize CPU overhead
            proc_attrs = ["pid", "name", "cpu_percent", "memory_percent", "status"]
            for proc in psutil.process_iter(attrs=proc_attrs):
                try:
                    info = proc.info
                    pid = int(info["pid"])
                    name = str(info["name"] or "unknown")
                    cpu_pct = float(info["cpu_percent"] or 0.0)
                    mem_pct = float(info["memory_percent"] or 0.0)
                    status = str(info["status"] or "unknown")

                    processes.append(
                        ProcessMetrics(
                            pid=pid,
                            name=name,
                            cpu_percent=cpu_pct,
                            memory_percent=round(mem_pct, 2),
                            status=status,
                        )
                    )
                except (
                    psutil.NoSuchProcess,
                    psutil.AccessDenied,
                    psutil.ZombieProcess,
                    KeyError,
                ):
                    # Process may have terminated or lacked query permissions; continue
                    continue

        except Exception as exc:
            self.logger.error("Failed to query process table: %s", exc)
            raise RuntimeError(f"Process table enumeration failed: {exc}") from exc

        # Sort primarily by CPU utilization descending, secondarily by memory percent descending
        processes.sort(key=lambda p: (p.cpu_percent, p.memory_percent), reverse=True)

        return processes[: self.max_processes]
