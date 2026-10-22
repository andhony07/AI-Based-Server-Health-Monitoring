"""Tests for explainable, evidence-based diagnostic recommendations engine.

Validates evidence extraction, threshold rule triggering, root-cause hypothesis
mapping, and actionable operational remediation outputs.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.database.models import SystemMetricRecord
from app.ml.diagnostics import (
    DiagnosticCategory,
    DiagnosticEngine,
    DiagnosticEvidence,
    DiagnosticRecommendation,
    DiagnosticReport,
    EvidenceLevel,
)
from app.ml.models import PredictionResult, RiskCategory
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)


@pytest.fixture
def engine() -> DiagnosticEngine:
    return DiagnosticEngine()


def test_nominal_telemetry_diagnostic_report(engine: DiagnosticEngine) -> None:
    """Verify nominal metrics yield an informative, clean baseline report."""
    metrics = {
        "cpu_percent": 15.0,
        "memory_percent": 35.0,
        "disk_percent": 40.0,
        "network_sent_kbps": 20.0,
        "network_recv_kbps": 40.0,
    }
    pred = PredictionResult(
        timestamp=datetime.now(timezone.utc),
        is_anomaly=False,
        anomaly_score=0.20,
        raw_decision_score=0.15,
        health_score=95.0,
        risk_category=RiskCategory.NORMAL,
        model_name="IsolationForestDetector",
        model_version="1.0.0",
    )

    report = engine.generate_report(prediction=pred, metrics=metrics)

    assert isinstance(report, DiagnosticReport)
    assert report.critical_count == 0
    assert report.warning_count == 0
    assert report.risk_category == RiskCategory.NORMAL
    assert len(report.recommendations) == 1
    assert report.recommendations[0].category == DiagnosticCategory.SYSTEM
    assert report.recommendations[0].severity == EvidenceLevel.INFO
    assert "Nominal" in report.recommendations[0].title


def test_cpu_saturation_diagnostic_rule(engine: DiagnosticEngine) -> None:
    """Verify CPU saturation triggers targeted process investigation recommendations."""
    metrics = {
        "cpu_percent": 96.5,
        "memory_percent": 45.0,
        "disk_percent": 50.0,
        "top_process_name": "stress_worker",
        "top_process_pid": 1042,
        "top_process_cpu_percent": 92.0,
    }
    pred = PredictionResult(
        timestamp=datetime.now(timezone.utc),
        is_anomaly=True,
        anomaly_score=0.88,
        raw_decision_score=-0.25,
        health_score=35.0,
        risk_category=RiskCategory.CRITICAL,
        model_name="IsolationForestDetector",
        model_version="1.0.0",
    )

    report = engine.generate_report(prediction=pred, metrics=metrics)

    assert report.critical_count >= 1
    cpu_recs = [r for r in report.recommendations if r.category == DiagnosticCategory.CPU]
    assert len(cpu_recs) == 1

    rec = cpu_recs[0]
    assert rec.severity == EvidenceLevel.CRITICAL
    assert "stress_worker" in rec.root_cause_hypothesis
    assert "1042" in rec.root_cause_hypothesis
    assert any("top" in s.lower() or "task manager" in s.lower() for s in rec.remediation_steps)
    assert any("renice" in s.lower() or "termination" in s.lower() for s in rec.remediation_steps)

    # Check evidence
    assert len(rec.evidence) >= 2
    ev_cpu = [e for e in rec.evidence if e.metric_name == "cpu_percent"][0]
    assert "96.5%" in str(ev_cpu.observed_value)


def test_memory_leak_diagnostic_rule(engine: DiagnosticEngine) -> None:
    """Verify memory exhaustion triggers leak diagnosis and heap profiling advice."""
    metrics = {
        "cpu_percent": 25.0,
        "memory_percent": 95.8,
        "disk_percent": 50.0,
        "top_process_name": "leaky_daemon",
        "top_process_memory_percent": 68.0,
    }
    report = engine.generate_report(metrics=metrics)

    mem_recs = [r for r in report.recommendations if r.category == DiagnosticCategory.MEMORY]
    assert len(mem_recs) == 1

    rec = mem_recs[0]
    assert rec.severity == EvidenceLevel.CRITICAL
    assert "leaky_daemon" in rec.root_cause_hypothesis
    assert any("heap" in s.lower() or "allocations" in s.lower() for s in rec.remediation_steps)
    assert any("restart" in s.lower() or "limits" in s.lower() for s in rec.remediation_steps)


def test_disk_saturation_diagnostic_rule(engine: DiagnosticEngine) -> None:
    """Verify disk capacity exhaustion triggers log rotation and cleanup advice."""
    metrics = {
        "cpu_percent": 20.0,
        "memory_percent": 30.0,
        "disk_percent": 96.0,
    }
    report = engine.generate_report(metrics=metrics)

    disk_recs = [r for r in report.recommendations if r.category == DiagnosticCategory.DISK]
    assert len(disk_recs) == 1

    rec = disk_recs[0]
    assert rec.severity == EvidenceLevel.CRITICAL
    assert any("pruning" in s.lower() or "rotation" in s.lower() or "temp" in s.lower() for s in rec.remediation_steps)


def test_network_surge_diagnostic_rule(engine: DiagnosticEngine) -> None:
    """Verify high bandwidth burst triggers socket review and traffic diagnosis."""
    features = {
        "network_bytes_recv_per_sec": 120_000_000.0,  # ~117 MB/s
        "network_bytes_sent_per_sec": 45_000_000.0,
    }
    report = engine.generate_report(features=features)

    net_recs = [r for r in report.recommendations if r.category == DiagnosticCategory.NETWORK]
    assert len(net_recs) == 1

    rec = net_recs[0]
    assert rec.severity == EvidenceLevel.HIGH
    assert any("socket" in s.lower() or "netstat" in s.lower() for s in rec.remediation_steps)


def test_ml_statistical_anomaly_rule(engine: DiagnosticEngine) -> None:
    """Verify ML anomaly score triggers statistical outlier analysis."""
    pred = PredictionResult(
        timestamp=datetime.now(timezone.utc),
        is_anomaly=True,
        anomaly_score=0.82,
        raw_decision_score=-0.18,
        health_score=40.0,
        risk_category=RiskCategory.HIGH,
        model_name="IsolationForestDetector",
        model_version="1.0.0",
    )
    report = engine.generate_report(prediction=pred)

    ml_recs = [r for r in report.recommendations if r.category == DiagnosticCategory.ANOMALY]
    assert len(ml_recs) == 1

    rec = ml_recs[0]
    assert "0.8200" in [e.observed_value for e in rec.evidence][0]
    assert any("audit log" in s.lower() or "deployments" in s.lower() for s in rec.remediation_steps)


def test_multi_resource_compound_pressure_sorting(engine: DiagnosticEngine) -> None:
    """Verify recommendations are ordered by severity (Critical first)."""
    metrics = {
        "cpu_percent": 96.0,
        "memory_percent": 94.0,
        "disk_percent": 95.0,
    }
    pred = PredictionResult(
        timestamp=datetime.now(timezone.utc),
        is_anomaly=True,
        anomaly_score=0.92,
        raw_decision_score=-0.35,
        health_score=15.0,
        risk_category=RiskCategory.CRITICAL,
        model_name="IsolationForestDetector",
        model_version="1.0.0",
    )

    report = engine.generate_report(prediction=pred, metrics=metrics)

    assert len(report.recommendations) >= 3
    # First recommendation must be Critical
    assert report.recommendations[0].severity == EvidenceLevel.CRITICAL
    assert report.critical_count >= 3


def test_diagnostic_report_serialization(engine: DiagnosticEngine) -> None:
    """Verify DiagnosticReport serializes cleanly to JSON dictionary."""
    metrics = {"cpu_percent": 88.0, "memory_percent": 40.0, "disk_percent": 45.0}
    report = engine.generate_report(metrics=metrics)

    data = report.to_dict()
    assert isinstance(data, dict)
    assert "timestamp" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    assert "root_cause_hypothesis" in data["recommendations"][0]


def test_empty_or_none_metrics_graceful_handling(engine: DiagnosticEngine) -> None:
    """Verify engine handles empty or None inputs without raising exceptions."""
    report = engine.generate_report(prediction=None, metrics=None, features=None)
    assert isinstance(report, DiagnosticReport)
    assert len(report.recommendations) >= 1
    assert report.recommendations[0].severity == EvidenceLevel.INFO
