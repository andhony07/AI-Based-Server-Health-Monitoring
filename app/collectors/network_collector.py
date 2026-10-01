"""Network traffic and throughput telemetry metric collector.

Collects cumulative network I/O counters and computes instantaneous upload and download
throughput (bytes per second) using elapsed monotonic time deltas.
"""

from __future__ import annotations

import time
from typing import Optional

import psutil

from app.collectors.base import BaseCollector
from app.models.metrics import NetworkMetrics


class NetworkCollector(BaseCollector[NetworkMetrics]):
    """Collector for network interface I/O counters and throughput rates."""

    def __init__(self) -> None:
        """Initialize the Network collector with rate tracking state."""
        super().__init__(name="network")
        self._last_bytes_sent: Optional[int] = None
        self._last_bytes_recv: Optional[int] = None
        self._last_timestamp: Optional[float] = None

    def collect(self) -> NetworkMetrics:
        """Harvest network counters and calculate data transfer throughput rates.

        Returns:
            NetworkMetrics containing cumulative counts and computed transfer rates.

        Raises:
            RuntimeError: If network I/O telemetry is completely unavailable.
        """
        try:
            counters = psutil.net_io_counters()
            if counters is None:
                raise RuntimeError("Host OS returned null network counters.")

            current_time = time.monotonic()
            bytes_sent = int(counters.bytes_sent)
            bytes_recv = int(counters.bytes_recv)
            packets_sent = int(counters.packets_sent)
            packets_recv = int(counters.packets_recv)

            bytes_sent_per_sec = 0.0
            bytes_recv_per_sec = 0.0

            # Calculate throughput only when a prior measurement exists
            if (
                self._last_timestamp is not None
                and self._last_bytes_sent is not None
                and self._last_bytes_recv is not None
            ):
                elapsed = current_time - self._last_timestamp

                # Guard against zero or negative elapsed time (e.g., immediate re-call)
                if elapsed > 0.0:
                    delta_sent = bytes_sent - self._last_bytes_sent
                    delta_recv = bytes_recv - self._last_bytes_recv

                    # Guard against counter resets (reboot, interface toggle, or 32-bit counter rollover)
                    if delta_sent >= 0 and delta_recv >= 0:
                        bytes_sent_per_sec = round(delta_sent / elapsed, 2)
                        bytes_recv_per_sec = round(delta_recv / elapsed, 2)
                    else:
                        self.logger.debug(
                            "Network counter reset detected; resetting throughput calculation."
                        )

            # Update state for next calculation cycle
            self._last_bytes_sent = bytes_sent
            self._last_bytes_recv = bytes_recv
            self._last_timestamp = current_time

            return NetworkMetrics(
                bytes_sent=bytes_sent,
                bytes_recv=bytes_recv,
                packets_sent=packets_sent,
                packets_recv=packets_recv,
                bytes_sent_per_sec=bytes_sent_per_sec,
                bytes_recv_per_sec=bytes_recv_per_sec,
            )
        except Exception as exc:
            self.logger.error("Failed to collect network metrics: %s", exc)
            raise RuntimeError(f"Network telemetry collection error: {exc}") from exc
