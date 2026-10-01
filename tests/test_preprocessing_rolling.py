"""Unit tests for the RollingWindowBuffer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.preprocessing.rolling import RollingWindowBuffer


class TestRollingWindowBuffer:
    """Test suite for the rolling window circular buffer."""

    def test_initial_sample_returns_defaults_without_crashing(self) -> None:
        """Verify behavior when buffer has only 1 sample (window not yet full)."""
        buf = RollingWindowBuffer(window_size=5, max_history_size=10)
        t0 = datetime.now(timezone.utc)
        buf.add(t0, {"cpu": 20.0, "ram": 40.0})

        assert buf.sample_count == 1
        # Delta requires 2 samples, returns default 0.0
        assert buf.get_delta("cpu") == 0.0
        assert buf.get_time_delta_seconds() == 0.0
        # Rolling stats over 1 sample equal the single observation
        assert buf.get_rolling_mean("cpu") == 20.0
        assert buf.get_rolling_max("cpu") == 20.0
        assert buf.get_rolling_min("cpu") == 20.0

    def test_delta_and_time_delta_calculation(self) -> None:
        """Verify delta calculation between consecutive samples and elapsed time."""
        buf = RollingWindowBuffer(window_size=5, max_history_size=10)
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=5.0)

        buf.add(t0, {"cpu": 20.0})
        buf.add(t1, {"cpu": 35.0})

        assert buf.get_delta("cpu") == 15.0  # 35.0 - 20.0
        assert buf.get_time_delta_seconds() == 5.0

    def test_rolling_mean_max_min_windowing(self) -> None:
        """Verify rolling stats compute accurately over a moving window of size 3."""
        buf = RollingWindowBuffer(window_size=3, max_history_size=10)
        t0 = datetime.now(timezone.utc)

        # Add 4 samples: 10, 20, 30, 40 -> with window_size=3, window contains [20, 30, 40]
        for idx, val in enumerate([10.0, 20.0, 30.0, 40.0]):
            buf.add(t0 + timedelta(seconds=idx * 5), {"cpu": val})

        assert buf.sample_count == 4
        # (20 + 30 + 40) / 3 = 30.0
        assert buf.get_rolling_mean("cpu") == 30.0
        assert buf.get_rolling_max("cpu") == 40.0
        assert buf.get_rolling_min("cpu") == 20.0

    def test_bounded_history_prevents_unbounded_growth(self) -> None:
        """Verify buffer never exceeds max_history_size."""
        max_hist = 5
        buf = RollingWindowBuffer(window_size=3, max_history_size=max_hist)
        t0 = datetime.now(timezone.utc)

        for i in range(20):
            buf.add(t0 + timedelta(seconds=i), {"val": float(i)})

        assert buf.sample_count == max_hist
        # Most recent sample was 19.0, oldest in buffer is 15.0
        assert buf.get_rolling_max("val") == 19.0

    def test_timestamp_regression_triggers_buffer_reset(self) -> None:
        """Verify timestamp moving backwards triggers an automatic buffer reset."""
        buf = RollingWindowBuffer(window_size=5, max_history_size=10)
        t0 = datetime.now(timezone.utc)

        buf.add(t0, {"cpu": 10.0})
        buf.add(t0 + timedelta(seconds=5), {"cpu": 20.0})
        assert buf.sample_count == 2

        # Timestamp jumps backward by 10 seconds
        buf.add(t0 - timedelta(seconds=10), {"cpu": 5.0})
        # Buffer was cleared, so only the new observation remains
        assert buf.sample_count == 1
        assert buf.get_rolling_mean("cpu") == 5.0
        assert buf.get_delta("cpu") == 0.0

    def test_large_time_gap_triggers_buffer_reset(self) -> None:
        """Verify large time gap (e.g. system resume after hours) triggers buffer reset."""
        buf = RollingWindowBuffer(window_size=5, max_history_size=10, max_gap_seconds=60.0)
        t0 = datetime.now(timezone.utc)

        buf.add(t0, {"cpu": 10.0})
        buf.add(t0 + timedelta(seconds=5), {"cpu": 15.0})
        assert buf.sample_count == 2

        # Jump 1 hour forward (> max_gap_seconds of 60s)
        buf.add(t0 + timedelta(hours=1), {"cpu": 30.0})
        assert buf.sample_count == 1
        assert buf.get_rolling_mean("cpu") == 30.0
