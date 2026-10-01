"""System telemetry metric collectors package.

Architectural Responsibility (Phase 2):
- Interface with system APIs using psutil to harvest CPU, memory, disk, network,
  and process health metrics.
- Support platform-specific telemetry collection (Windows initially, Linux later).
- Provide periodic and on-demand sampling interfaces with graceful error isolation.
"""

from __future__ import annotations

from app.collectors.base import BaseCollector
from app.collectors.cpu_collector import CPUCollector
from app.collectors.disk_collector import DiskCollector
from app.collectors.memory_collector import MemoryCollector
from app.collectors.network_collector import NetworkCollector
from app.collectors.process_collector import ProcessCollector
from app.collectors.system_collector import SystemCollector

__all__ = [
    "BaseCollector",
    "CPUCollector",
    "DiskCollector",
    "MemoryCollector",
    "NetworkCollector",
    "ProcessCollector",
    "SystemCollector",
]
