"""Tests for deterministic anomaly simulation subsystem.

Validates synthetic scenario generation, determinism, schema consistency,
boundary compliance, and ML pipeline integration.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import load_config
from app.database.service import PersistenceService
from app.ml.anomaly_detector import IsolationForestDetector
from app.ml.feature_schema import validate_feature_vector_finite
from app.ml.models import RiskCategory
from app.ml.prediction_service import PredictionService
from app.ml.simulation import (
    DeterministicAnomalySimulator,
    SCENARIO_PROFILES,
    ScenarioProfile,
    SimulationResult,
    SimulationScenario,
)
from app.models.metrics import SystemMetrics
from app.preprocessing.pipeline import PreprocessingPipeline
from app.preprocessing.validator import MetricsValidator


@pytest.fixture
def simulator() -> DeterministicAnomalySimulator:
    return DeterministicAnomalySimulator()


@pytest.fixture
def validator() -> MetricsValidator:
    return MetricsValidator()


def test_simulation_scenarios_enum_and_profiles(simulator: DeterministicAnomalySimulator) -> None:
    """Verify all defined scenarios have complete profile metadata."""
    profiles = simulator.get_profiles()
    assert len(profiles) == len(SimulationScenario)

    for sc in SimulationScenario:
        prof = simulator.get_profile(sc)
        assert isinstance(prof, ScenarioProfile)
        assert prof.scenario == sc
        assert len(prof.name) > 0
        assert len(prof.description) > 0
        assert isinstance(prof.expected_risk, RiskCategory)


def test_deterministic_metric_generation(simulator: DeterministicAnomalySimulator) -> None:
    """Verify identical seeds produce byte-for-byte identical metrics."""
    fixed_ts = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)
    m1 = simulator.generate_metrics(SimulationScenario.CPU_SPIKE, timestamp=fixed_ts, seed=123)
    m2 = simulator.generate_metrics(SimulationScenario.CPU_SPIKE, timestamp=fixed_ts, seed=123)

    assert m1.cpu.utilization_percent == m2.cpu.utilization_percent
    assert m1.memory.utilization_percent == m2.memory.utilization_percent
    assert m1.disk.utilization_percent == m2.disk.utilization_percent
    assert m1.network.bytes_sent_per_sec == m2.network.bytes_sent_per_sec
    assert len(m1.processes) == len(m2.processes)
    assert m1.processes[0].name == m2.processes[0].name
    assert m1.processes[0].cpu_percent == m2.processes[0].cpu_percent


def test_metric_bounds_and_validity(simulator: DeterministicAnomalySimulator, validator: MetricsValidator) -> None:
    """Verify all generated scenarios pass data validation without errors."""
    for sc in SimulationScenario:
        m = simulator.generate_metrics(sc, seed=42)
        assert isinstance(m, SystemMetrics)
        assert 0.0 <= m.cpu.utilization_percent <= 100.0
        assert 0.0 <= m.memory.utilization_percent <= 100.0
        assert 0.0 <= m.disk.utilization_percent <= 100.0
        assert m.network.bytes_sent_per_sec >= 0.0
        assert m.network.bytes_recv_per_sec >= 0.0

        val_res = validator.validate(m)
        assert val_res.is_valid is True
        assert val_res.has_errors is False


def test_cpu_spike_scenario_characteristics(simulator: DeterministicAnomalySimulator) -> None:
    """Verify CPU spike scenario manifests runaway compute process."""
    m = simulator.generate_metrics(SimulationScenario.CPU_SPIKE)
    assert m.cpu.utilization_percent >= 90.0
    assert len(m.processes) > 0

    top_proc = max(m.processes, key=lambda p: p.cpu_percent)
    assert top_proc.name == "stress_worker"
    assert top_proc.cpu_percent >= 80.0


def test_memory_leak_scenario_characteristics(simulator: DeterministicAnomalySimulator) -> None:
    """Verify memory leak scenario manifests memory exhaustion process."""
    m = simulator.generate_metrics(SimulationScenario.MEMORY_LEAK)
    assert m.memory.utilization_percent >= 90.0
    assert len(m.processes) > 0

    top_proc = max(m.processes, key=lambda p: p.memory_percent)
    assert top_proc.name == "leaky_daemon"
    assert top_proc.memory_percent >= 60.0


def test_disk_saturation_scenario_characteristics(simulator: DeterministicAnomalySimulator) -> None:
    """Verify disk saturation scenario manifests critical storage pressure."""
    m = simulator.generate_metrics(SimulationScenario.DISK_SATURATION)
    assert m.disk.utilization_percent >= 92.0
    assert m.disk.free_bytes < 10 * 1024**3  # Less than 10 GB free


def test_network_storm_scenario_characteristics(simulator: DeterministicAnomalySimulator) -> None:
    """Verify network storm scenario generates massive I/O throughput."""
    m = simulator.generate_metrics(SimulationScenario.NETWORK_STORM)
    assert m.network.bytes_recv_per_sec >= 50_000_000.0  # > 50 MB/s
    assert m.network.bytes_sent_per_sec >= 25_000_000.0  # > 25 MB/s


def test_sequence_generation(simulator: DeterministicAnomalySimulator) -> None:
    """Verify generate_sequence creates sequential ramp-up telemetry."""
    seq = simulator.generate_sequence(SimulationScenario.CPU_SPIKE, steps=5, interval_seconds=2.0)
    assert len(seq) == 5

    # Check ascending timestamps
    for i in range(1, len(seq)):
        assert seq[i].timestamp > seq[i - 1].timestamp

    # Final step should be the full CPU spike
    assert seq[-1].cpu.utilization_percent >= 90.0


def test_end_to_end_simulation_dry_run(simulator: DeterministicAnomalySimulator) -> None:
    """Verify simulate dry-run passes through ML preprocessing without persisting."""
    pipeline = PreprocessingPipeline()
    pred_service = PredictionService(auto_load=False)

    sim_res = simulator.simulate(
        SimulationScenario.CPU_SPIKE,
        pipeline=pipeline,
        prediction_service=pred_service,
        persist=False,
    )

    assert isinstance(sim_res, SimulationResult)
    assert sim_res.scenario == SimulationScenario.CPU_SPIKE
    assert sim_res.persisted is False
    assert sim_res.metric_id is None
    assert sim_res.feature_id is None

    # Check 39 features are finite
    is_finite, non_finites = validate_feature_vector_finite(sim_res.processed.feature_vector.features)
    assert is_finite is True
    assert len(non_finites) == 0

    # Prediction evaluated
    assert sim_res.prediction is not None
    assert sim_res.prediction.risk_category in (RiskCategory.HIGH, RiskCategory.CRITICAL)


def test_end_to_end_simulation_with_persistence(simulator: DeterministicAnomalySimulator, tmp_path: Path) -> None:
    """Verify simulate with persistence saves records to SQLite."""
    settings = load_config(
        database_path=tmp_path / "sim_test.db",
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        logs_dir=tmp_path / "logs",
        db_auto_init=True,
    )
    pers_service = PersistenceService(settings=settings)
    pipeline = PreprocessingPipeline(settings=settings)
    pred_service = PredictionService(settings=settings, auto_load=False)

    sim_res = simulator.simulate(
        SimulationScenario.MEMORY_LEAK,
        pipeline=pipeline,
        prediction_service=pred_service,
        persistence_service=pers_service,
        persist=True,
    )

    assert sim_res.persisted is True
    assert sim_res.metric_id is not None
    assert sim_res.feature_id is not None
    assert sim_res.metric_id > 0
    assert sim_res.feature_id > 0

    # Verify queryable from DB
    saved_metrics = pers_service.get_latest_metrics(limit=1)
    assert len(saved_metrics) == 1
    assert saved_metrics[0].memory_percent >= 90.0


def test_ml_prediction_behavior_on_simulated_anomalies(simulator: DeterministicAnomalySimulator) -> None:
    """Verify ML risk and health response across nominal vs anomaly scenarios."""
    pipeline = PreprocessingPipeline()
    pred_service = PredictionService(auto_load=False)

    # 1. Nominal
    nom_res = simulator.simulate(SimulationScenario.NOMINAL, pipeline=pipeline, prediction_service=pred_service)
    assert nom_res.prediction.risk_category == RiskCategory.NORMAL
    assert nom_res.prediction.health_score is not None
    assert nom_res.prediction.health_score >= 80.0

    # 2. Compound Multi-Resource Pressure
    multi_res = simulator.simulate(SimulationScenario.MULTI_RESOURCE_PRESSURE, pipeline=pipeline, prediction_service=pred_service)
    assert multi_res.prediction.risk_category == RiskCategory.CRITICAL
    assert multi_res.prediction.health_score is not None
    assert multi_res.prediction.health_score < 75.0

