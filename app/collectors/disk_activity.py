"""Disk activity provider subsystem using native operating system performance counters.

Provides reliable disk active time percentage (% Disk Time) and I/O throughput
using Windows Performance Data Helper (PDH) via ctypes on Windows, with graceful
fallback to a null provider on unsupported platforms or when counters are unavailable.
"""

from __future__ import annotations

import ctypes
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger("app.collectors.disk_activity")


@dataclass(frozen=True)
class DiskActivityMetrics:
    """Snapshot of physical disk activity and throughput.

    Attributes:
        active_time_percent: Percentage of measurement interval the disk was busy (0.0 - 100.0).
            None if counter is unavailable or unprimed.
        read_bytes_per_sec: Rate of data read from disk in bytes/sec, or None if unavailable.
        write_bytes_per_sec: Rate of data written to disk in bytes/sec, or None if unavailable.
    """

    active_time_percent: Optional[float] = None
    read_bytes_per_sec: Optional[float] = None
    write_bytes_per_sec: Optional[float] = None


class BaseDiskActivityProvider(ABC):
    """Abstract base provider for disk activity metrics."""

    @abstractmethod
    def get_activity(self) -> DiskActivityMetrics:
        """Harvest disk activity metrics.

        Returns:
            DiskActivityMetrics instance.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Release any underlying system handles or queries."""
        pass


class NullDiskActivityProvider(BaseDiskActivityProvider):
    """Fallback provider when native disk activity counters are unsupported or unavailable."""

    def get_activity(self) -> DiskActivityMetrics:
        return DiskActivityMetrics(
            active_time_percent=None,
            read_bytes_per_sec=None,
            write_bytes_per_sec=None,
        )


class WindowsPdhDiskActivityProvider(BaseDiskActivityProvider):
    """Harvests physical disk active time and throughput using Windows PDH.

    Queries:
        - \\PhysicalDisk(_Total)\\% Disk Time
        - \\PhysicalDisk(_Total)\\Disk Read Bytes/sec
        - \\PhysicalDisk(_Total)\\Disk Write Bytes/sec
    """

    def __init__(self, prime_on_init: bool = True) -> None:
        """Initialize Windows PDH query and performance counters.

        Args:
            prime_on_init: If True, executes an initial collection to prime rate counters.
        """
        self._initialized = False
        self._h_query = None
        self._h_counter_active = None
        self._h_counter_read = None
        self._h_counter_write = None
        self._last_collect_time: float = 0.0

        if sys.platform != "win32":
            logger.debug("WindowsPdhDiskActivityProvider disabled: non-Windows platform (%s).", sys.platform)
            return

        self._setup_pdh(prime_on_init=prime_on_init)

    def _setup_pdh(self, prime_on_init: bool) -> None:
        """Set up PDH query and add performance counters."""
        try:
            from ctypes import byref, c_double, c_ulong, wintypes

            pdh = ctypes.windll.pdh

            class PDH_FmtCounterValue(ctypes.Structure):
                _fields_ = [("CStatus", c_ulong), ("doubleValue", c_double)]

            self._PDH_FmtCounterValue = PDH_FmtCounterValue
            self._PDH_FMT_DOUBLE = 0x00000200

            h_query = wintypes.HANDLE()
            status = pdh.PdhOpenQueryW(None, 0, byref(h_query))
            if status != 0:
                logger.debug("PdhOpenQueryW failed with status: 0x%08X", status)
                return

            self._h_query = h_query

            # Add counters
            h_active = wintypes.HANDLE()
            h_read = wintypes.HANDLE()
            h_write = wintypes.HANDLE()

            res_active = pdh.PdhAddCounterW(
                self._h_query,
                "\\PhysicalDisk(_Total)\\% Disk Time",
                0,
                byref(h_active),
            )
            res_read = pdh.PdhAddCounterW(
                self._h_query,
                "\\PhysicalDisk(_Total)\\Disk Read Bytes/sec",
                0,
                byref(h_read),
            )
            res_write = pdh.PdhAddCounterW(
                self._h_query,
                "\\PhysicalDisk(_Total)\\Disk Write Bytes/sec",
                0,
                byref(h_write),
            )

            if res_active == 0:
                self._h_counter_active = h_active
            else:
                logger.debug("PdhAddCounterW active time failed: 0x%08X", res_active)

            if res_read == 0:
                self._h_counter_read = h_read
            if res_write == 0:
                self._h_counter_write = h_write

            self._initialized = True

            if prime_on_init:
                pdh.PdhCollectQueryData(self._h_query)
                self._last_collect_time = time.monotonic()

            logger.debug("Windows PDH Disk Activity provider successfully initialized.")
        except Exception as exc:
            logger.debug("Windows PDH initialization encountered an error: %s", exc)
            self.close()

    def get_activity(self) -> DiskActivityMetrics:
        """Collect current disk active percentage and throughput rates."""
        if not self._initialized or not self._h_query:
            return DiskActivityMetrics(None, None, None)

        try:
            pdh = ctypes.windll.pdh
            from ctypes import byref

            now = time.monotonic()
            elapsed = now - self._last_collect_time if self._last_collect_time > 0 else 0.0

            # If unprimed or called with virtually zero elapsed time, do a small sleep to sample
            if self._last_collect_time == 0.0 or elapsed < 0.05:
                pdh.PdhCollectQueryData(self._h_query)
                time.sleep(0.05)

            status = pdh.PdhCollectQueryData(self._h_query)
            self._last_collect_time = time.monotonic()

            if status != 0:
                logger.debug("PdhCollectQueryData returned status: 0x%08X", status)
                return DiskActivityMetrics(None, None, None)

            active_pct: Optional[float] = None
            read_rate: Optional[float] = None
            write_rate: Optional[float] = None

            if self._h_counter_active:
                val = self._PDH_FmtCounterValue()
                res = pdh.PdhGetFormattedCounterValue(
                    self._h_counter_active,
                    self._PDH_FMT_DOUBLE,
                    None,
                    byref(val),
                )
                if res == 0 and val.CStatus == 0:
                    # PhysicalDisk % Disk Time can theoretically exceed 100% on multi-disk stripes;
                    # clamp standard active time between 0.0 and 100.0% for task-manager consistency
                    raw_val = float(val.doubleValue)
                    active_pct = round(max(0.0, min(100.0, raw_val)), 2)

            if self._h_counter_read:
                val = self._PDH_FmtCounterValue()
                res = pdh.PdhGetFormattedCounterValue(
                    self._h_counter_read,
                    self._PDH_FMT_DOUBLE,
                    None,
                    byref(val),
                )
                if res == 0 and val.CStatus == 0:
                    read_rate = round(max(0.0, float(val.doubleValue)), 2)

            if self._h_counter_write:
                val = self._PDH_FmtCounterValue()
                res = pdh.PdhGetFormattedCounterValue(
                    self._h_counter_write,
                    self._PDH_FMT_DOUBLE,
                    None,
                    byref(val),
                )
                if res == 0 and val.CStatus == 0:
                    write_rate = round(max(0.0, float(val.doubleValue)), 2)

            return DiskActivityMetrics(
                active_time_percent=active_pct,
                read_bytes_per_sec=read_rate,
                write_bytes_per_sec=write_rate,
            )
        except Exception as exc:
            logger.debug("Error querying PDH disk activity: %s", exc)
            return DiskActivityMetrics(None, None, None)

    def close(self) -> None:
        """Release PDH query handle."""
        if self._h_query:
            try:
                pdh = ctypes.windll.pdh
                pdh.PdhCloseQuery(self._h_query)
            except Exception:
                pass
            self._h_query = None
        self._initialized = False


def create_default_disk_activity_provider() -> BaseDiskActivityProvider:
    """Factory creating the best available disk activity provider for the current OS."""
    if sys.platform == "win32":
        try:
            provider = WindowsPdhDiskActivityProvider(prime_on_init=True)
            if provider._initialized:
                return provider
        except Exception as err:
            logger.debug("Failed to instantiate WindowsPdhDiskActivityProvider: %s", err)

    return NullDiskActivityProvider()
