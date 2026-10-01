"""Unit tests for ML risk categorization subsystem."""

from __future__ import annotations

import pytest

from app.core.config import Settings, load_config
from app.ml.models import RiskCategory
from app.ml.risk_analyzer import RiskAnalyzer


class TestRiskAnalyzer:
    """Tests covering risk level assignment, threshold evaluation, and saturation escalation."""

    def test_default_threshold_categories(self) -> None:
        """Verify standard anomaly score brackets map to expected RiskCategories."""
        analyzer = RiskAnalyzer()

        assert analyzer.evaluate_risk(0.10) == RiskCategory.NORMAL
        assert analyzer.evaluate_risk(0.34) == RiskCategory.NORMAL
        assert analyzer.evaluate_risk(0.35) == RiskCategory.LOW
        assert analyzer.evaluate_risk(0.50) == RiskCategory.LOW
        assert analyzer.evaluate_risk(0.55) == RiskCategory.MODERATE
        assert analyzer.evaluate_risk(0.70) == RiskCategory.MODERATE
        assert analyzer.evaluate_risk(0.75) == RiskCategory.HIGH
        assert analyzer.evaluate_risk(0.85) == RiskCategory.HIGH
        assert analyzer.evaluate_risk(0.90) == RiskCategory.CRITICAL
        assert analyzer.evaluate_risk(0.99) == RiskCategory.CRITICAL

    def test_custom_thresholds_from_settings(self) -> None:
        """Verify custom settings modify risk evaluation thresholds."""
        custom_settings = load_config(
            ml_risk_threshold_low=0.20,
            ml_risk_threshold_moderate=0.40,
            ml_risk_threshold_high=0.60,
            ml_risk_threshold_critical=0.80,
        )
        analyzer = RiskAnalyzer(settings=custom_settings)


        assert analyzer.evaluate_risk(0.15) == RiskCategory.NORMAL
        assert analyzer.evaluate_risk(0.25) == RiskCategory.LOW
        assert analyzer.evaluate_risk(0.45) == RiskCategory.MODERATE
        assert analyzer.evaluate_risk(0.65) == RiskCategory.HIGH
        assert analyzer.evaluate_risk(0.85) == RiskCategory.CRITICAL

    def test_critical_hardware_saturation_override(self) -> None:
        """Verify critical resource exhaustion escalates risk to CRITICAL even if anomaly score is low."""
        analyzer = RiskAnalyzer()

        # Low anomaly score (0.10), but CPU is 98% -> Should escalate to CRITICAL
        risk_cpu = analyzer.evaluate_risk(
            anomaly_score=0.10,
            cpu_percent=98.0,
            memory_percent=40.0,
            disk_percent=30.0,
        )
        assert risk_cpu == RiskCategory.CRITICAL

        # Low anomaly score (0.10), but RAM is 96% -> Should escalate to CRITICAL
        risk_ram = analyzer.evaluate_risk(
            anomaly_score=0.10,
            cpu_percent=20.0,
            memory_percent=96.0,
            disk_percent=30.0,
        )
        assert risk_ram == RiskCategory.CRITICAL

        # Low anomaly score (0.10), but Disk is 96% -> Should escalate to CRITICAL
        risk_disk = analyzer.evaluate_risk(
            anomaly_score=0.10,
            cpu_percent=20.0,
            memory_percent=30.0,
            disk_percent=96.0,
        )
        assert risk_disk == RiskCategory.CRITICAL

    def test_explain_risk(self) -> None:
        """Verify explain_risk provides human-readable context on risk assignment."""
        analyzer = RiskAnalyzer()
        explanation = analyzer.explain_risk(
            risk_category=RiskCategory.HIGH,
            anomaly_score=0.85,
            health_score=45.0,
        )
        assert "High" in explanation
        assert "0.85" in explanation
        assert "45.0" in explanation
