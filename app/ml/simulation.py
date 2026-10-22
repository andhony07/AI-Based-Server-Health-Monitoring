"""Safe, deterministic anomaly simulation subsystem.

Generates reproducible, synthetic hardware telemetry snapshots and progressions
representing standard operational anomaly profiles (e.g., CPU thread runaway,
memory exhaustion leak, disk volume saturation, network traffic storm, compound pressure)
without performing actual OS-level fault injection or stressing host hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional, Union

from app.database.service import PersistenceService
from app.ml.models import PredictionResult, RiskCategory
from app.ml.prediction_service import PredictionService
from app.models.metrics import (
    CPUMetrics,
    DiskMetrics,
    DiskPartitionMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessMetrics,
    SystemMetrics,
)
from app.preprocessing.pipeline import PreprocessingPipeline, ProcessedTelemetry


class SimulationScenario(str, Enum):
    """Supported deterministic anomaly simulation profiles."""

    NOMINAL = "nominal"
    CPU_SPIKE = "cpu_spike"
    MEMORY_LEAK = "memory_leak"
    DISK_SATURATION = "disk_saturation"
    NETWORK_STORM = "network_storm"
    MULTI_RESOURCE_PRESSURE = "multi_resource_pressure"


@dataclass(frozen=True)
class ScenarioProfile:
    """Descriptive metadata profile for an anomaly simulation scenario."""

    scenario: SimulationScenario
    name: str
    description: str
    stress_subsystem: str
    expected_risk: RiskCategory
    is_anomaly_expected: bool


SCENARIO_PROFILES: dict[SimulationScenario, ScenarioProfile] = {
    SimulationScenario.NOMINAL: ScenarioProfile(
        scenario=SimulationScenario.NOMINAL,
        name="Nominal Baseline",
        description="Normal, healthy system operation within standard baseline thresholds (~18% CPU, ~40% RAM, ~42% Disk).",
        stress_subsystem="None (Healthy)",
        expected_risk=RiskCategory.NORMAL,
        is_anomaly_expected=False,
    ),
    SimulationScenario.CPU_SPIKE: ScenarioProfile(
        scenario=SimulationScenario.CPU_SPIKE,
        name="CPU Thread Runaway / Spike",
        description="Sudden CPU saturation (96.5%) dominated by a single compute-intensive runaway process ('stress_worker').",
        stress_subsystem="CPU",
        expected_risk=RiskCategory.CRITICAL,
        is_anomaly_expected=True,
    ),
    SimulationScenario.MEMORY_LEAK: ScenarioProfile(
        scenario=SimulationScenario.MEMORY_LEAK,
        name="Memory Exhaustion Leak",
        description="Rapid RAM consumption (95.4%) driven by an unconstrained memory-allocating daemon ('leaky_daemon').",
        stress_subsystem="Memory (RAM)",
        expected_risk=RiskCategory.CRITICAL,
        is_anomaly_expected=True,
    ),
    SimulationScenario.DISK_SATURATION: ScenarioProfile(
        scenario=SimulationScenario.DISK_SATURATION,
        name="Disk Volume Saturation",
        description="Near-total filesystem storage capacity exhaustion (97.5% used, only 2.5 GB free space remaining).",
        stress_subsystem="Storage (Disk)",
        expected_risk=RiskCategory.CRITICAL,
        is_anomaly_expected=True,
    ),
    SimulationScenario.NETWORK_STORM: ScenarioProfile(
        scenario=SimulationScenario.NETWORK_STORM,
        name="Network Traffic Storm",
        description="Massive inbound throughput burst (145 MB/s RX, 80 MB/s TX) representing an I/O surge or ingress spike.",
        stress_subsystem="Network I/O",
        expected_risk=RiskCategory.MODERATE,
        is_anomaly_expected=True,
    ),
    SimulationScenario.MULTI_RESOURCE_PRESSURE: ScenarioProfile(
        scenario=SimulationScenario.MULTI_RESOURCE_PRESSURE,
        name="Compound Multi-Resource Saturation",
        description="Cascading compound crisis with concurrent CPU (96%), RAM (94%), and Disk (96%) severe saturation.",
        stress_subsystem="CPU / RAM / Disk",
        expected_risk=RiskCategory.CRITICAL,
        is_anomaly_expected=True,
    ),
}


@dataclass(frozen=True)
class SimulationResult:
    """Outcome of an end-to-end simulated telemetry run through the ML pipeline.

    Attributes:
        scenario: The executed simulation scenario.
        profile: Companion descriptive metadata.
        metrics: Generated synthetic SystemMetrics.
        processed: Preprocessed telemetry with engineered 39-feature vector.
        prediction: ML prediction result (anomaly score, health score, risk category).
        persisted: Whether the sample was committed to the SQLite database.
        metric_id: Primary key of inserted metrics record, if persisted.
        feature_id: Primary key of inserted feature vector record, if persisted.
    """

    scenario: SimulationScenario
    profile: ScenarioProfile
    metrics: SystemMetrics
    processed: ProcessedTelemetry
    prediction: PredictionResult
    persisted: bool = False
    metric_id: Optional[int] = None
    feature_id: Optional[int] = None


class DeterministicAnomalySimulator:
    """Purely synthetic, deterministic anomaly generator and pipeline executor.

    Generates reproducible telemetry frames without applying OS-level stress.
    Every generated metric conforms strictly to physical boundaries and the
    39-feature preprocessing schema.
    """

    def __init__(self) -> None:
        """Initialize the deterministic anomaly simulator."""
        pass

    @classmethod
    def get_profiles(cls) -> list[ScenarioProfile]:
        """Return the list of all available simulation scenario profiles."""
        return list(SCENARIO_PROFILES.values())

    @classmethod
    def get_profile(cls, scenario: Union[SimulationScenario, str]) -> ScenarioProfile:
        """Retrieve profile metadata for a specific scenario."""
        sc_enum = SimulationScenario(scenario) if isinstance(scenario, str) else scenario
        return SCENARIO_PROFILES[sc_enum]

    def generate_metrics(
        self,
        scenario: Union[SimulationScenario, str],
        timestamp: Optional[datetime] = None,
        seed: int = 42,
        **overrides: Any,
    ) -> SystemMetrics:
        """Generate a deterministic synthetic SystemMetrics snapshot.

        Args:
            scenario: Simulation scenario enum or string key.
            timestamp: Optional UTC timestamp for the sample. Defaults to now (UTC).
            seed: Integer seed controlling deterministic micro-variations.
            **overrides: Optional explicit parameter overrides (e.g., cpu_percent=99.0).

        Returns:
            Populated, schema-valid SystemMetrics dataclass instance.
        """
        sc = SimulationScenario(scenario) if isinstance(scenario, str) else scenario
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Micro-variation offset derived deterministically from seed in [-0.5, 0.5]
        offset = ((seed * 1103515245 + 12345) % 100) / 100.0 - 0.5

        if sc == SimulationScenario.NOMINAL:
            cpu_val = overrides.get("cpu_percent", round(18.5 + offset * 2, 2))
            ram_val = overrides.get("memory_percent", round(42.0 + offset * 2, 2))
            disk_val = overrides.get("disk_percent", round(45.0 + offset * 1, 2))
            net_tx_bps = overrides.get("net_tx_bps", round(25_000.0 + offset * 2000, 2))
            net_rx_bps = overrides.get("net_rx_bps", round(48_000.0 + offset * 3000, 2))

            processes = [
                ProcessMetrics(pid=101, name="systemd", cpu_percent=1.2, memory_percent=1.0, status="running"),
                ProcessMetrics(pid=210, name="python", cpu_percent=4.5, memory_percent=3.2, status="running"),
                ProcessMetrics(pid=330, name="postgres", cpu_percent=2.8, memory_percent=4.1, status="sleeping"),
                ProcessMetrics(pid=450, name="nginx", cpu_percent=1.5, memory_percent=1.8, status="running"),
            ]

        elif sc == SimulationScenario.CPU_SPIKE:
            cpu_val = overrides.get("cpu_percent", min(99.5, max(90.0, round(96.5 + offset * 2, 2))))
            ram_val = overrides.get("memory_percent", round(45.0 + offset * 2, 2))
            disk_val = overrides.get("disk_percent", round(48.0 + offset * 1, 2))
            net_tx_bps = overrides.get("net_tx_bps", 35_000.0)
            net_rx_bps = overrides.get("net_rx_bps", 50_000.0)

            runaway_cpu = round(cpu_val * 0.94, 1)
            processes = [
                ProcessMetrics(pid=1042, name="stress_worker", cpu_percent=runaway_cpu, memory_percent=4.5, status="running"),
                ProcessMetrics(pid=210, name="python", cpu_percent=2.1, memory_percent=3.2, status="running"),
                ProcessMetrics(pid=330, name="postgres", cpu_percent=1.5, memory_percent=4.0, status="sleeping"),
            ]

        elif sc == SimulationScenario.MEMORY_LEAK:
            cpu_val = overrides.get("cpu_percent", round(28.0 + offset * 2, 2))
            ram_val = overrides.get("memory_percent", min(99.5, max(90.0, round(95.4 + offset * 1.5, 2))))
            disk_val = overrides.get("disk_percent", round(52.0 + offset * 1, 2))
            net_tx_bps = overrides.get("net_tx_bps", 28_000.0)
            net_rx_bps = overrides.get("net_rx_bps", 60_000.0)

            runaway_ram = round(ram_val * 0.72, 1)
            processes = [
                ProcessMetrics(pid=2088, name="leaky_daemon", cpu_percent=8.2, memory_percent=runaway_ram, status="running"),
                ProcessMetrics(pid=330, name="postgres", cpu_percent=3.1, memory_percent=5.5, status="sleeping"),
                ProcessMetrics(pid=210, name="python", cpu_percent=2.0, memory_percent=3.5, status="running"),
            ]

        elif sc == SimulationScenario.DISK_SATURATION:
            cpu_val = overrides.get("cpu_percent", round(32.0 + offset * 2, 2))
            ram_val = overrides.get("memory_percent", round(55.0 + offset * 2, 2))
            disk_val = overrides.get("disk_percent", min(99.8, max(92.0, round(97.5 + offset * 1.0, 2))))
            net_tx_bps = overrides.get("net_tx_bps", 15_000.0)
            net_rx_bps = overrides.get("net_rx_bps", 22_000.0)

            processes = [
                ProcessMetrics(pid=330, name="postgres", cpu_percent=4.2, memory_percent=6.5, status="sleeping"),
                ProcessMetrics(pid=3410, name="log_rotator", cpu_percent=6.5, memory_percent=2.1, status="running"),
                ProcessMetrics(pid=210, name="python", cpu_percent=2.5, memory_percent=3.5, status="running"),
            ]

        elif sc == SimulationScenario.NETWORK_STORM:
            cpu_val = overrides.get("cpu_percent", round(54.0 + offset * 2, 2))
            ram_val = overrides.get("memory_percent", round(48.0 + offset * 2, 2))
            disk_val = overrides.get("disk_percent", round(44.0 + offset * 1, 2))
            # 145 MB/s RX, 80 MB/s TX
            net_tx_bps = overrides.get("net_tx_bps", round(80_000_000.0 + offset * 2_000_000, 2))
            net_rx_bps = overrides.get("net_rx_bps", round(145_000_000.0 + offset * 3_000_000, 2))

            processes = [
                ProcessMetrics(pid=450, name="nginx", cpu_percent=24.5, memory_percent=5.0, status="running"),
                ProcessMetrics(pid=5120, name="io_pump", cpu_percent=18.2, memory_percent=4.1, status="running"),
                ProcessMetrics(pid=210, name="python", cpu_percent=3.5, memory_percent=3.0, status="running"),
            ]

        elif sc == SimulationScenario.MULTI_RESOURCE_PRESSURE:
            cpu_val = overrides.get("cpu_percent", min(99.5, max(92.0, round(96.0 + offset * 1.5, 2))))
            ram_val = overrides.get("memory_percent", min(99.5, max(90.0, round(94.2 + offset * 1.5, 2))))
            disk_val = overrides.get("disk_percent", min(99.8, max(92.0, round(96.8 + offset * 1.0, 2))))
            net_tx_bps = overrides.get("net_tx_bps", 75_000_000.0)
            net_rx_bps = overrides.get("net_rx_bps", 110_000_000.0)

            processes = [
                ProcessMetrics(pid=1042, name="stress_worker", cpu_percent=68.5, memory_percent=12.0, status="running"),
                ProcessMetrics(pid=2088, name="leaky_daemon", cpu_percent=14.0, memory_percent=62.0, status="running"),
                ProcessMetrics(pid=450, name="nginx", cpu_percent=10.5, memory_percent=8.0, status="running"),
            ]
        else:
            raise ValueError(f"Unknown simulation scenario: {scenario}")

        # Assemble physical sub-component models
        logical_cores = 8
        per_core = [min(100.0, max(0.0, round(cpu_val + ((i % 3) - 1) * 3.0, 1))) for i in range(logical_cores)]
        cpu_metrics = CPUMetrics(
            utilization_percent=cpu_val,
            logical_cores=logical_cores,
            physical_cores=4,
            per_core_percent=per_core,
        )

        total_ram_bytes = 16 * 1024 * 1024 * 1024  # 16 GB
        used_ram_bytes = int(total_ram_bytes * (ram_val / 100.0))
        avail_ram_bytes = total_ram_bytes - used_ram_bytes
        memory_metrics = MemoryMetrics(
            total_bytes=total_ram_bytes,
            available_bytes=avail_ram_bytes,
            used_bytes=used_ram_bytes,
            utilization_percent=ram_val,
        )

        total_disk_bytes = 100 * 1024 * 1024 * 1024  # 100 GB
        used_disk_bytes = int(total_disk_bytes * (disk_val / 100.0))
        free_disk_bytes = total_disk_bytes - used_disk_bytes
        partition = DiskPartitionMetrics(
            mount_point="C:\\",
            total_bytes=total_disk_bytes,
            used_bytes=used_disk_bytes,
            free_bytes=free_disk_bytes,
            utilization_percent=disk_val,
            device="HarddiskVolume1",
            fstype="NTFS",
        )
        disk_metrics = DiskMetrics(
            partitions=[partition],
            total_bytes=total_disk_bytes,
            used_bytes=used_disk_bytes,
            free_bytes=free_disk_bytes,
            utilization_percent=disk_val,
        )

        network_metrics = NetworkMetrics(
            bytes_sent=10_000_000 + int(net_tx_bps * 60),
            bytes_recv=20_000_000 + int(net_rx_bps * 60),
            packets_sent=50_000,
            packets_recv=85_000,
            bytes_sent_per_sec=net_tx_bps,
            bytes_recv_per_sec=net_rx_bps,
        )

        return SystemMetrics(
            timestamp=ts,
            cpu=cpu_metrics,
            memory=memory_metrics,
            disk=disk_metrics,
            network=network_metrics,
            processes=processes,
            errors=[],
        )

    def generate_sequence(
        self,
        scenario: Union[SimulationScenario, str],
        steps: int = 5,
        start_time: Optional[datetime] = None,
        interval_seconds: float = 5.0,
        seed: int = 42,
    ) -> list[SystemMetrics]:
        """Generate a sequential progression of telemetry samples ending in the target anomaly state.

        Provides realistic delta and rolling window metric changes for the preprocessing pipeline.

        Args:
            scenario: Target anomaly scenario enum or string key.
            steps: Number of sequential samples to generate (>= 1).
            start_time: Timestamp of the initial sample.
            interval_seconds: Gap between samples in seconds.
            seed: Base random seed for determinism.

        Returns:
            List of SystemMetrics ordered chronologically.
        """
        if steps < 1:
            raise ValueError("steps must be >= 1")

        base_time = start_time or (datetime.now(timezone.utc) - timedelta(seconds=interval_seconds * steps))
        results: list[SystemMetrics] = []

        sc = SimulationScenario(scenario) if isinstance(scenario, str) else scenario

        for i in range(steps):
            step_ts = base_time + timedelta(seconds=i * interval_seconds)
            step_seed = seed + i * 17

            if sc == SimulationScenario.NOMINAL or steps == 1 or i == steps - 1:
                # Last step is full target scenario
                target_sc = sc if (i == steps - 1 or steps == 1) else SimulationScenario.NOMINAL
                results.append(self.generate_metrics(target_sc, timestamp=step_ts, seed=step_seed))
            else:
                # Progressive ramp-up towards target scenario
                ramp_ratio = (i + 1) / float(steps)
                nom_m = self.generate_metrics(SimulationScenario.NOMINAL, timestamp=step_ts, seed=step_seed)
                anom_m = self.generate_metrics(sc, timestamp=step_ts, seed=step_seed)

                # Interpolate CPU, RAM, Disk
                interp_cpu = round(nom_m.cpu.utilization_percent + (anom_m.cpu.utilization_percent - nom_m.cpu.utilization_percent) * ramp_ratio, 2)
                interp_ram = round(nom_m.memory.utilization_percent + (anom_m.memory.utilization_percent - nom_m.memory.utilization_percent) * ramp_ratio, 2)
                interp_disk = round(nom_m.disk.utilization_percent + (anom_m.disk.utilization_percent - nom_m.disk.utilization_percent) * ramp_ratio, 2)
                interp_tx = nom_m.network.bytes_sent_per_sec + (anom_m.network.bytes_sent_per_sec - nom_m.network.bytes_sent_per_sec) * ramp_ratio
                interp_rx = nom_m.network.bytes_recv_per_sec + (anom_m.network.bytes_recv_per_sec - nom_m.network.bytes_recv_per_sec) * ramp_ratio

                step_metrics = self.generate_metrics(
                    sc,
                    timestamp=step_ts,
                    seed=step_seed,
                    cpu_percent=interp_cpu,
                    memory_percent=interp_ram,
                    disk_percent=interp_disk,
                    net_tx_bps=interp_tx,
                    net_rx_bps=interp_rx,
                )
                results.append(step_metrics)

        return results

    def simulate(
        self,
        scenario: Union[SimulationScenario, str],
        pipeline: Optional[PreprocessingPipeline] = None,
        prediction_service: Optional[PredictionService] = None,
        persistence_service: Optional[PersistenceService] = None,
        persist: bool = False,
        seed: int = 42,
        **kwargs: Any,
    ) -> SimulationResult:
        """Execute a simulated anomaly sample through the complete ML pipeline.

        Args:
            scenario: The simulation scenario to execute.
            pipeline: PreprocessingPipeline instance (created with defaults if None).
            prediction_service: PredictionService instance (created with defaults if None).
            persistence_service: Optional PersistenceService for DB persistence.
            persist: If True and persistence_service is provided, commits sample to SQLite.
            seed: Deterministic seed.
            **kwargs: Metric parameter overrides passed to generate_metrics.

        Returns:
            Populated SimulationResult.
        """
        sc = SimulationScenario(scenario) if isinstance(scenario, str) else scenario
        profile = self.get_profile(sc)

        pipe = pipeline or PreprocessingPipeline()
        pred_svc = prediction_service or PredictionService()

        metrics = self.generate_metrics(sc, seed=seed, **kwargs)
        processed = pipe.process(metrics)
        prediction = pred_svc.predict(processed)

        persisted = False
        metric_id: Optional[int] = None
        feature_id: Optional[int] = None

        if persist and persistence_service is not None:
            persist_res = persistence_service.persist_sample(metrics, processed)
            if persist_res.success:
                persisted = True
                metric_id = persist_res.metric_id
                feature_id = persist_res.feature_id

        return SimulationResult(
            scenario=sc,
            profile=profile,
            metrics=metrics,
            processed=processed,
            prediction=prediction,
            persisted=persisted,
            metric_id=metric_id,
            feature_id=feature_id,
        )
