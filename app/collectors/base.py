"""Base collector abstraction.

Defines a standardized interface and error handling contract for all
telemetry metric collectors.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.core.logging_config import get_logger

# Generic type parameter representing the metric model returned by the collector
T = TypeVar("T")


class BaseCollector(ABC, Generic[T]):
    """Abstract base class for system telemetry collectors.

    Subclasses must implement the `collect()` method to sample and return
    their respective metric data model.
    """

    def __init__(self, name: str) -> None:
        """Initialize base collector.

        Args:
            name: Human-readable identifier for the collector used in logging.
        """
        self.name: str = name
        self.logger: logging.Logger = get_logger(f"app.collectors.{name}")

    @abstractmethod
    def collect(self) -> T:
        """Harvest and return typed telemetry metrics.

        Returns:
            The collector-specific metric data model instance.

        Raises:
            Exception: If an unrecoverable hardware or OS telemetry failure occurs.
        """
        raise NotImplementedError("Subclasses must implement collect()")
