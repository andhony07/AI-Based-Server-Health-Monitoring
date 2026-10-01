"""System health scoring calculation subsystem.

Computes a deterministic, transparent composite health score bounded in [0.0, 100.0]
derived from anomaly detection severity and hardware resource stress indicators.
"""

from __future__ import annotations

from typing import Any, Optional

from app.core.logging_config import get_logger
from app.ml.models import AnomalyResult, HealthScoreResult

logger = get_logger("app.ml.health_score")


class HealthScoreCalculator:
    """Calculates deterministic heuristic system health scores bounded in [0.0, 100.0].

    Health scoring is an empirical heuristic combining statistical anomaly scores
    and immediate resource saturation thresholds. It is not an ISO or medical certification
    of hardware integrity.
    """

    def __init__(
        self,
        anomaly_weight: float = 60.0,
        resource_stress_weight: float = 40.0,
    ) -> None:
        """Initialize health score calculator.

        Args:
            anomaly_weight: Maximum points deducted for statistical anomaly severity (default 60.0).
            resource_stress_weight: Maximum points deducted for hardware resource saturation (default 40.0).
        """
        self.anomaly_weight: float = anomaly_weight
        self.resource_stress_weight: float = resource_stress_weight
        self.max_resource_penalty: float = resource_stress_weight

    def calculate(
        self,
        anomaly_result: Optional[AnomalyResult] = None,
        features: Optional[dict[str, Any]] = None,
        *,
        anomaly_score: Optional[float] = None,
        cpu_percent: Optional[float] = None,
        memory_percent: Optional[float] = None,
        disk_percent: Optional[float] = None,
    ) -> HealthScoreResult:
        """Calculate a composite health score based on anomaly scores and resource stress.

        Formula:
            Base = 100.0
            Anomaly Penalty = normalized_anomaly_score * 60.0
            CPU Stress Penalty = max(0, (cpu_percent - 80) / 20) * 15.0
            RAM Stress Penalty = max(0, (ram_percent - 85) / 15) * 15.0
            Disk Stress Penalty = max(0, (disk_percent - 90) / 10) * 10.0
            Health Score = clamp(100.0 - (Anomaly Penalty + Resource Penalties), 0.0, 100.0)

        Args:
            anomaly_result: Optional AnomalyResult from anomaly detector.
            features: Optional dictionary of feature values.
            anomaly_score: Optional direct normalized anomaly score float in [0.0, 1.0].
            cpu_percent: Optional direct CPU utilization percentage.
            memory_percent: Optional direct memory utilization percentage.
            disk_percent: Optional direct disk utilization percentage.

        Returns:
            Populated HealthScoreResult instance.
        """
        # Resolve effective anomaly score
        norm_anomaly: Optional[float] = None
        if anomaly_score is not None:
            norm_anomaly = max(0.0, min(1.0, float(anomaly_score)))
        elif anomaly_result is not None:
            norm_anomaly = max(0.0, min(1.0, float(anomaly_result.normalized_score)))

        # Resolve resource metrics
        feat_dict = dict(features) if features else {}
        cpu = cpu_percent if cpu_percent is not None else float(feat_dict.get("cpu_utilization_percent", 0.0))
        ram = memory_percent if memory_percent is not None else float(feat_dict.get("memory_utilization_percent", 0.0))
        disk = disk_percent if disk_percent is not None else float(feat_dict.get("disk_utilization_percent", 0.0))

        if norm_anomaly is None and not features and cpu_percent is None and memory_percent is None and disk_percent is None:
            return HealthScoreResult(
                score=None,
                status="unavailable",
                contributing_factors={},
                explanation="No telemetry features or anomaly detection results available for evaluation.",
            )

        contributions: dict[str, float] = {}
        total_deductions = 0.0

        # 1. Anomaly Penalty (up to 60.0 points)
        if norm_anomaly is not None:
            anomaly_penalty = round(norm_anomaly * self.anomaly_weight, 2)
            contributions["anomaly_penalty"] = anomaly_penalty
            total_deductions += anomaly_penalty
        else:
            contributions["anomaly_penalty"] = 0.0

        # 2. Resource Saturation Stress Penalties (up to 40.0 points total)
        # CPU Penalty (up to 15 points if CPU > 80%)
        cpu_penalty = 0.0
        if cpu > 80.0:
            cpu_ratio = min(1.0, max(0.0, (cpu - 80.0) / 20.0))
            cpu_penalty = round(cpu_ratio * 15.0, 2)
        contributions["cpu_stress_penalty"] = cpu_penalty
        contributions["cpu_stress_deduction"] = cpu_penalty
        total_deductions += cpu_penalty

        # RAM Penalty (up to 15 points if RAM > 85%)
        ram_penalty = 0.0
        if ram > 85.0:
            ram_ratio = min(1.0, max(0.0, (ram - 85.0) / 15.0))
            ram_penalty = round(ram_ratio * 15.0, 2)
        contributions["ram_stress_penalty"] = ram_penalty
        contributions["ram_stress_deduction"] = ram_penalty
        total_deductions += ram_penalty

        # Disk Penalty (up to 10 points if Disk > 90%)
        disk_penalty = 0.0
        if disk > 90.0:
            disk_ratio = min(1.0, max(0.0, (disk - 90.0) / 10.0))
            disk_penalty = round(disk_ratio * 10.0, 2)
        contributions["disk_stress_penalty"] = disk_penalty
        contributions["disk_stress_deduction"] = disk_penalty
        total_deductions += disk_penalty

        score = max(0.0, min(100.0, 100.0 - total_deductions))
        score = round(score, 2)

        # Status categorization
        if score >= 85.0:
            status = "Optimal"
        elif score >= 70.0:
            status = "Good"
        elif score >= 45.0:
            status = "Degraded"
        else:
            status = "Critical"

        explanation_parts = []
        if norm_anomaly is None:
            explanation_parts.append("ML anomaly model unavailable; score reflects hardware saturation only.")
        elif anomaly_result and anomaly_result.is_anomaly:
            explanation_parts.append(
                f"Statistical anomaly flagged (score {anomaly_result.normalized_score:.2f})."
            )
        if total_deductions == 0.0:
            explanation_parts.append("System operating within normal baseline envelope.")
        else:
            explanation_parts.append(f"Deductions applied: {total_deductions:.1f} pts total.")

        return HealthScoreResult(
            score=score,
            status=status,
            contributing_factors=contributions,
            explanation=" ".join(explanation_parts),
        )

