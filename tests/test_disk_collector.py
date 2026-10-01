"""Unit and integration tests for the Disk storage telemetry collector."""

from __future__ import annotations

from unittest import mock

import pytest

from app.collectors.disk_collector import DiskCollector
from app.models.metrics import DiskMetrics, DiskPartitionMetrics


class TestDiskCollector:
    """Test suite for disk partition telemetry collection."""

    def test_collect_returns_valid_metrics_structure(self) -> None:
        """Verify collect returns valid DiskMetrics with accessible local partitions."""
        collector = DiskCollector()
        metrics = collector.collect()

        assert isinstance(metrics, DiskMetrics)
        assert isinstance(metrics.partitions, list)
        assert len(metrics.partitions) >= 1

        for part in metrics.partitions:
            assert isinstance(part, DiskPartitionMetrics)
            assert isinstance(part.mount_point, str)
            assert part.total_bytes > 0
            assert part.free_bytes >= 0
            assert part.used_bytes >= 0
            assert 0.0 <= part.utilization_percent <= 100.0
            assert part.total_gb > 0

        assert metrics.total_bytes > 0
        assert metrics.used_bytes > 0
        assert 0.0 <= metrics.utilization_percent <= 100.0

    @mock.patch("psutil.disk_usage")
    @mock.patch("psutil.disk_partitions")
    def test_inaccessible_partition_skipped_gracefully(
        self, mock_parts: mock.MagicMock, mock_usage: mock.MagicMock
    ) -> None:
        """Verify that an inaccessible drive or optical disc is skipped without crashing."""
        part_c = mock.MagicMock(mountpoint="C:\\", device="C:\\", fstype="NTFS")
        part_d = mock.MagicMock(mountpoint="D:\\", device="D:\\", fstype="CDFS")
        mock_parts.return_value = [part_c, part_d]

        usage_c = mock.MagicMock(total=1000, used=400, free=600, percent=40.0)

        def usage_side_effect(path: str) -> mock.MagicMock:
            if path == "C:\\":
                return usage_c
            raise PermissionError("Drive D:\\ device not ready")

        mock_usage.side_effect = usage_side_effect

        collector = DiskCollector()
        metrics = collector.collect()

        assert len(metrics.partitions) == 1
        assert metrics.partitions[0].mount_point == "C:\\"
        assert metrics.total_bytes == 1000
        assert metrics.used_bytes == 400
        assert metrics.free_bytes == 600
        assert metrics.utilization_percent == 40.0

    @mock.patch("psutil.disk_usage")
    @mock.patch("psutil.disk_partitions")
    def test_duplicate_mount_points_deduplicated(
        self, mock_parts: mock.MagicMock, mock_usage: mock.MagicMock
    ) -> None:
        """Verify duplicate mount points are not queried multiple times."""
        part_c1 = mock.MagicMock(mountpoint="C:\\", device="C:\\", fstype="NTFS")
        part_c2 = mock.MagicMock(mountpoint="c:\\", device="C:\\", fstype="NTFS")
        mock_parts.return_value = [part_c1, part_c2]

        mock_usage.return_value = mock.MagicMock(
            total=1000, used=500, free=500, percent=50.0
        )

        collector = DiskCollector()
        metrics = collector.collect()

        assert len(metrics.partitions) == 1
        assert mock_usage.call_count == 1

    @mock.patch("psutil.disk_partitions", side_effect=OSError("Drive enum failed"))
    def test_partition_enum_error_raises_runtime_error(
        self, _mock_parts: mock.MagicMock
    ) -> None:
        """Verify failure to query partition table raises RuntimeError."""
        collector = DiskCollector()
        with pytest.raises(RuntimeError, match="Disk partition enumeration failed"):
            collector.collect()
