"""Unit tests for transparent system health score calculation."""

from __future__ import annotations

import pytest

from app.ml.health_score import HealthScoreCalculator


class TestHealthScoreCalculator:
    """Tests covering health score formula, deductions, boundary clamping, and status categories."""

    def test_init_defaults(self) -> None:
        """Verify default weights and thresholds."""
        calc = HealthScoreCalculator()
        assert calc.anomaly_weight == 60.0
        assert calc.max_resource_penalty == 40.0

    def test_perfect_health_score(self) -> None:
        """Verify baseline score of 100.0 when anomaly score is 0 and resources are idle."""
        calc = HealthScoreCalculator()
        res = calc.calculate(
            anomaly_score=0.0,
            cpu_percent=10.0,
            memory_percent=20.0,
            disk_percent=30.0,
        )
        assert pytest.approx(res.health_score, abs=0.1) == 100.0
        assert res.status == "Optimal"
        assert res.anomaly_deduction == 0.0
        assert res.resource_stress_deduction == 0.0

    def test_pure_anomaly_deduction(self) -> None:
        """Verify anomaly score deducts up to 60 points when anomaly_score is 1.0."""
        calc = HealthScoreCalculator()
        # Anomaly score = 0.5 -> 30 points deducted
        res = calc.calculate(
            anomaly_score=0.5,
            cpu_percent=10.0,
            memory_percent=20.0,
            disk_percent=30.0,
        )
        assert pytest.approx(res.health_score, abs=0.1) == 70.0
        assert pytest.approx(res.anomaly_deduction, abs=0.1) == 30.0

        # Anomaly score = 1.0 -> 60 points deducted
        res_full = calc.calculate(
            anomaly_score=1.0,
            cpu_percent=10.0,
            memory_percent=20.0,
            disk_percent=30.0,
        )
        assert pytest.approx(res_full.health_score, abs=0.1) == 40.0
        assert pytest.approx(res_full.anomaly_deduction, abs=0.1) == 60.0

    def test_resource_stress_deductions(self) -> None:
        """Verify high CPU, RAM, and Disk utilization apply appropriate penalties."""
        calc = HealthScoreCalculator()

        # High CPU only (>80%): 100% CPU -> 15 pts
        res_cpu = calc.calculate(
            anomaly_score=0.0,
            cpu_percent=100.0,
            memory_percent=20.0,
            disk_percent=30.0,
        )
        assert pytest.approx(res_cpu.resource_stress_deduction, abs=0.5) == 15.0
        assert pytest.approx(res_cpu.health_score, abs=0.5) == 85.0
        assert "cpu_stress_deduction" in res_cpu.contributing_factors

        # High RAM only (>85%): 100% RAM -> 15 pts
        res_ram = calc.calculate(
            anomaly_score=0.0,
            cpu_percent=10.0,
            memory_percent=100.0,
            disk_percent=30.0,
        )
        assert pytest.approx(res_ram.resource_stress_deduction, abs=0.5) == 15.0
        assert pytest.approx(res_ram.health_score, abs=0.5) == 85.0

        # High Disk only (>90%): 100% Disk -> 10 pts
        res_disk = calc.calculate(
            anomaly_score=0.0,
            cpu_percent=10.0,
            memory_percent=20.0,
            disk_percent=100.0,
        )
        assert pytest.approx(res_disk.resource_stress_deduction, abs=0.5) == 10.0
        assert pytest.approx(res_disk.health_score, abs=0.5) == 90.0

    def test_compound_worst_case_bounded_to_zero(self) -> None:
        """Verify maximum anomaly and maximum resource stress floor at 0.0."""
        calc = HealthScoreCalculator()
        res = calc.calculate(
            anomaly_score=1.0,
            cpu_percent=100.0,
            memory_percent=100.0,
            disk_percent=100.0,
        )
        # 100 - (60 + 15 + 15 + 10) = 0.0
        assert res.health_score == 0.0
        assert res.status == "Critical"

    def test_status_categories(self) -> None:
        """Verify status labels match health score thresholds."""
        calc = HealthScoreCalculator()
        assert calc.calculate(anomaly_score=0.1).status in ("Optimal", "Good")
        assert calc.calculate(anomaly_score=0.6).status in ("Degraded", "Critical")

    def test_clamp_extreme_inputs(self) -> None:
        """Verify inputs outside standard bounds do not cause negative scores or NaN."""
        calc = HealthScoreCalculator()
        res = calc.calculate(
            anomaly_score=2.5,  # Above 1.0
            cpu_percent=150.0,
            memory_percent=200.0,
            disk_percent=120.0,
        )
        assert 0.0 <= res.health_score <= 100.0
        assert res.health_score == 0.0
