"""Risk tier classification and analysis subsystem.

Translates continuous anomaly detection scores and health assessment metrics
into standardized, human-actionable operational risk tiers.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from app.core.config import Settings, get_settings
from app.ml.models import AnomalyResult, HealthScoreResult, RiskCategory


class RiskAnalyzer:
    """Categorizes system operational state into standardized RiskCategory tiers.

    Categorization is based strictly on statistical anomaly scores and hardware stress.
    It does not claim to represent a calibrated failure probability.
    """

    def __init__(
        self,
        threshold_low: float = 0.35,
        threshold_moderate: float = 0.55,
        threshold_high: float = 0.75,
        threshold_critical: float = 0.90,
        settings: Optional[Settings] = None,
    ) -> None:
        """Initialize the risk analyzer with configurable tier boundaries.

        Args:
            threshold_low: Lower bound for Low risk tier (default 0.35).
            threshold_moderate: Lower bound for Moderate risk tier (default 0.55).
            threshold_high: Lower bound for High risk tier (default 0.75).
            threshold_critical: Lower bound for Critical risk tier (default 0.90).
            settings: Optional Settings container to pull configured thresholds from.
        """
        cfg = settings or get_settings()
        self.threshold_low = threshold_low if settings is None else cfg.ml_risk_threshold_low
        self.threshold_moderate = (
            threshold_moderate if settings is None else cfg.ml_risk_threshold_moderate
        )
        self.threshold_high = threshold_high if settings is None else cfg.ml_risk_threshold_high
        self.threshold_critical = (
            threshold_critical if settings is None else cfg.ml_risk_threshold_critical
        )

    def evaluate_risk(
        self,
        anomaly_input: Optional[Union[AnomalyResult, float]] = None,
        health_result: Optional[Union[HealthScoreResult, float]] = None,
        features: Optional[dict[str, Any]] = None,
        *,
        anomaly_score: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        memory_percent: Optional[float] = None,
        disk_percent: Optional[float] = None,
    ) -> RiskCategory:
        """Assign an operational RiskCategory based on anomaly score and resource stress.

        Evaluation Priority:
            1. If normalized anomaly score >= threshold_critical -> CRITICAL
            2. If severe multi-resource saturation (e.g. CPU > 95%, RAM > 95%, Disk > 95%) -> CRITICAL
            3. If normalized anomaly score >= threshold_high -> HIGH
            4. If health score < 40.0 -> HIGH
            5. If normalized anomaly score >= threshold_moderate -> MODERATE
            6. If health score < 70.0 -> MODERATE
            7. If normalized anomaly score >= threshold_low -> LOW
            8. Otherwise -> NORMAL

        Args:
            anomaly_input: Optional AnomalyResult or direct normalized anomaly score float.
            health_result: Optional HealthScoreResult or direct health score float.
            features: Optional dictionary of feature metrics for immediate saturation check.
            anomaly_score: Optional direct normalized anomaly score keyword argument.
            cpu_percent: Optional direct CPU utilization percentage.
            memory_percent: Optional direct RAM utilization percentage.
            disk_percent: Optional direct Disk utilization percentage.

        Returns:
            Assigned RiskCategory enum value.
        """
        # Resolve anomaly score
        score: float = 0.0
        if anomaly_score is not None:
            score = float(anomaly_score)
        elif isinstance(anomaly_input, (int, float)):
            score = float(anomaly_input)
        elif isinstance(anomaly_input, AnomalyResult):
            score = float(anomaly_input.normalized_score)

        # Resolve health score
        health: float = 100.0
        if isinstance(health_result, (int, float)):
            health = float(health_result)
        elif isinstance(health_result, HealthScoreResult) and health_result.score is not None:
            health = float(health_result.score)

        # Check for immediate critical hardware saturation
        is_severe_saturation = False
        feat_dict = dict(features) if features else {}
        cpu = cpu_percent if cpu_percent is not None else float(feat_dict.get("cpu_utilization_percent", 0.0))
        ram = memory_percent if memory_percent is not None else float(feat_dict.get("memory_utilization_percent", 0.0))
        disk = disk_percent if disk_percent is not None else float(feat_dict.get("disk_utilization_percent", 0.0))

        if cpu >= 95.0 or ram >= 95.0 or disk >= 95.0:
            is_severe_saturation = True

        # Tier 1: CRITICAL
        if score >= self.threshold_critical or is_severe_saturation or health <= 20.0:
            return RiskCategory.CRITICAL

        # Tier 2: HIGH
        if score >= self.threshold_high or health <= 40.0:
            return RiskCategory.HIGH

        # Tier 3: MODERATE
        if score >= self.threshold_moderate or health <= 70.0:
            return RiskCategory.MODERATE

        # Tier 4: LOW
        if score >= self.threshold_low or health <= 85.0:
            return RiskCategory.LOW

        # Tier 5: NORMAL
        return RiskCategory.NORMAL

    def explain_risk(
        self,
        risk_category: RiskCategory,
        anomaly_score: float,
        health_score: Optional[float] = None,
    ) -> str:
        """Provide a concise explanation for an assigned risk category.

        Args:
            risk_category: The assigned RiskCategory.
            anomaly_score: The normalized anomaly score.
            health_score: Optional composite health score.

        Returns:
            Human-readable explanation string.
        """
        health_part = f"Health Score: {health_score:.1f}/100" if health_score is not None else "Health Score: N/A"
        return (
            f"Risk Level: {risk_category.value}. "
            f"Evaluated anomaly score: {anomaly_score:.2f} (Critical threshold: {self.threshold_critical:.2f}). "
            f"{health_part}."
        )

