"""Bounded rolling-window telemetry buffer and statistics computer.

Maintains a bounded sliding window of historical observations, computing rolling
mean, max, min, and previous-sample deltas without unbounded memory growth or forward-look bias.
Handles startup ramp-up, irregular sampling intervals, and timestamp regressions safely.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.logging_config import get_logger


@dataclass(frozen=True)
class HistoricalSample:
    """Historical telemetry record stored in rolling window buffer.

    Attributes:
        timestamp: Time of sample acquisition.
        values: Dictionary of numerical metric values.
    """

    timestamp: datetime
    values: dict[str, float]


class RollingWindowBuffer:
    """Bounded circular buffer providing rolling window statistics and step deltas."""

    def __init__(
        self,
        window_size: int = 12,
        max_history_size: int = 60,
        max_gap_seconds: float = 300.0,
    ) -> None:
        """Initialize rolling window buffer.

        Args:
            window_size: Number of most recent samples to include in rolling calculations.
            max_history_size: Hard upper bound on samples retained in memory.
            max_gap_seconds: Maximum permissible time gap between consecutive samples
                before triggering an automatic history reset (defaults to 300.0s / 5 mins).
        """
        self.window_size = max(1, window_size)
        self.max_history_size = max(self.window_size, max_history_size)
        self.max_gap_seconds = max_gap_seconds
        self.logger = get_logger("app.preprocessing.rolling")

        self._buffer: deque[HistoricalSample] = deque(maxlen=self.max_history_size)

    @property
    def sample_count(self) -> int:
        """Number of samples currently retained in the rolling buffer."""
        return len(self._buffer)

    def add(self, timestamp: datetime, values: dict[str, float]) -> None:
        """Append a new telemetry observation into the circular buffer.

        Detects timestamp regressions (time moving backwards) and excessive gaps,
        resetting history if necessary to prevent corrupted delta and moving window calculations.

        Args:
            timestamp: Observation acquisition time.
            values: Mapping of metric names to numerical values.
        """
        if self._buffer:
            last_sample = self._buffer[-1]
            elapsed = (timestamp - last_sample.timestamp).total_seconds()

            # Timestamp regression detection (NTP adjustment or host clock sync backwards)
            if elapsed < 0:
                self.logger.warning(
                    "Timestamp regression detected (last=%s, current=%s, elapsed=%.2fs). "
                    "Resetting rolling buffer to protect statistical integrity.",
                    last_sample.timestamp,
                    timestamp,
                    elapsed,
                )
                self.clear()

            # Excessive sampling gap detection (system suspend/resume or long downtime)
            elif elapsed > self.max_gap_seconds:
                self.logger.info(
                    "Large telemetry gap detected (elapsed=%.2fs > max=%.2fs). "
                    "Resetting rolling history to prevent stale rate calculations.",
                    elapsed,
                    self.max_gap_seconds,
                )
                self.clear()

        self._buffer.append(HistoricalSample(timestamp=timestamp, values=dict(values)))

    def get_delta(self, key: str, default: float = 0.0) -> float:
        """Compute the difference between the most recent and previous observation (current - previous).

        Args:
            key: Metric attribute name.
            default: Value returned if fewer than 2 samples exist in history.

        Returns:
            The step delta (current - previous), or default.
        """
        if len(self._buffer) < 2:
            return default

        curr_val = self._buffer[-1].values.get(key)
        prev_val = self._buffer[-2].values.get(key)

        if curr_val is None or prev_val is None:
            return default

        return round(curr_val - prev_val, 4)

    def get_time_delta_seconds(self, default: float = 0.0) -> float:
        """Compute the elapsed seconds between the most recent and previous sample.

        Args:
            default: Value returned if fewer than 2 samples exist in history.

        Returns:
            Elapsed time in seconds (current_time - previous_time), or default.
        """
        if len(self._buffer) < 2:
            return default

        curr_time = self._buffer[-1].timestamp
        prev_time = self._buffer[-2].timestamp
        elapsed = (curr_time - prev_time).total_seconds()
        return max(0.0, round(elapsed, 4))

    def get_rolling_mean(self, key: str, default: float = 0.0) -> float:
        """Calculate the rolling average over up to window_size recent samples.

        Args:
            key: Metric attribute name.
            default: Value returned if no samples contain the metric.

        Returns:
            Calculated rolling arithmetic mean.
        """
        window_samples = self._get_active_window()
        vals = [s.values[key] for s in window_samples if key in s.values]
        if not vals:
            return default
        return round(sum(vals) / len(vals), 4)

    def get_rolling_max(self, key: str, default: float = 0.0) -> float:
        """Calculate the rolling maximum over up to window_size recent samples.

        Args:
            key: Metric attribute name.
            default: Value returned if no samples contain the metric.

        Returns:
            Calculated rolling maximum.
        """
        window_samples = self._get_active_window()
        vals = [s.values[key] for s in window_samples if key in s.values]
        if not vals:
            return default
        return round(max(vals), 4)

    def get_rolling_min(self, key: str, default: float = 0.0) -> float:
        """Calculate the rolling minimum over up to window_size recent samples.

        Args:
            key: Metric attribute name.
            default: Value returned if no samples contain the metric.

        Returns:
            Calculated rolling minimum.
        """
        window_samples = self._get_active_window()
        vals = [s.values[key] for s in window_samples if key in s.values]
        if not vals:
            return default
        return round(min(vals), 4)

    def _get_active_window(self) -> list[HistoricalSample]:
        """Return the sub-list of the most recent samples bounded by window_size."""
        count = min(len(self._buffer), self.window_size)
        if count == 0:
            return []
        # Slice from the end of the circular buffer
        buf_list = list(self._buffer)
        return buf_list[-count:]

    def clear(self) -> None:
        """Reset and empty all historical samples from buffer."""
        self._buffer.clear()
