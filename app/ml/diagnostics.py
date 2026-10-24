"""Explainable, evidence-based diagnostic recommendations engine.

Analyzes telemetry snapshots, engineered features, and ML anomaly predictions
to produce human-auditable, evidence-backed diagnostic reports with concrete
root-cause hypotheses and prioritized operational remediation steps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union

from app.database.models import SystemMetricRecord
from app.ml.models import PredictionResult, RiskCategory
from app.models.metrics import SystemMetrics


class EvidenceLevel(str, Enum):
    """Severity or confidence level of diagnostic evidence."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INFO = "INFO"


class DiagnosticCategory(str, Enum):
    """Subsystem domain category for diagnostic findings."""

    CPU = "CPU"
    MEMORY = "Memory"
    DISK = "Disk"
    NETWORK = "Network"
    ANOMALY = "ML Outlier"
    SYSTEM = "System Health"


@dataclass(frozen=True)
class DiagnosticEvidence:
    """An individual piece of empirical telemetry evidence supporting a recommendation.

    Attributes:
        metric_name: Identifier of the metric or feature examined.
        observed_value: Actual numeric or textual observation.
        threshold: Nominal boundary or threshold reference.
        level: Evidence severity classification.
        description: Human-readable explanation of why this observation is significant.
    """

    metric_name: str
    observed_value: Any
    threshold: str
    level: EvidenceLevel
    description: str

    def to_dict(self) -> dict[str, Any]:
        """Convert evidence item to dictionary."""
        return {
            "metric_name": self.metric_name,
            "observed_value": self.observed_value,
            "threshold": self.threshold,
            "level": self.level.value,
            "description": self.description,
        }


@dataclass(frozen=True)
class DiagnosticRecommendation:
    """Actionable operational recommendation backed by verified evidence.

    Attributes:
        id: Unique identifier for the recommendation rule.
        category: Affected subsystem domain.
        severity: Operational urgency level.
        title: Descriptive headline summary.
        summary: Concise explanation of the condition.
        root_cause_hypothesis: Suspected engineering cause.
        evidence: List of supporting telemetry measurements.
        remediation_steps: Ordered list of practical remediation actions.
        target_component: Optional process name, drive mount, or interface identified.
    """

    id: str
    category: DiagnosticCategory
    severity: EvidenceLevel
    title: str
    summary: str
    root_cause_hypothesis: str
    evidence: list[DiagnosticEvidence]
    remediation_steps: list[str]
    target_component: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert recommendation to dictionary."""
        return {
            "id": self.id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "summary": self.summary,
            "root_cause_hypothesis": self.root_cause_hypothesis,
            "evidence": [e.to_dict() for e in self.evidence],
            "remediation_steps": list(self.remediation_steps),
            "target_component": self.target_component,
        }


@dataclass(frozen=True)
class DiagnosticReport:
    """Consolidated diagnostic report generated for an evaluation snapshot.

    Attributes:
        timestamp: Time of report generation (UTC).
        overall_health_score: Composite system health score in [0.0, 100.0].
        risk_category: Assigned operational risk classification.
        anomaly_score: Normalized anomaly probability indicator in [0.0, 1.0].
        is_anomaly: Binary anomaly flag.
        recommendations: Prioritized list of actionable diagnostic findings.
        summary_headline: High-level operational summary.
        primary_concern: Most urgent subsystem or anomaly identified.
        critical_count: Number of critical-severity findings.
        warning_count: Number of high- or moderate-severity findings.
    """

    timestamp: datetime
    overall_health_score: Optional[float]
    risk_category: RiskCategory
    anomaly_score: float
    is_anomaly: bool
    recommendations: list[DiagnosticRecommendation]
    summary_headline: str
    primary_concern: Optional[str] = None
    critical_count: int = 0
    warning_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostic report to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_health_score": round(self.overall_health_score, 1) if self.overall_health_score is not None else None,
            "risk_category": self.risk_category.value,
            "anomaly_score": round(self.anomaly_score, 4),
            "is_anomaly": self.is_anomaly,
            "summary_headline": self.summary_headline,
            "primary_concern": self.primary_concern,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "recommendations": [r.to_dict() for r in self.recommendations],
        }


class DiagnosticEngine:
    """Evaluates telemetry observations and ML inferences against diagnostic rules.

    Generates explainable, evidence-backed diagnostic reports with actionable
    remediation guidance.
    """

    def __init__(
        self,
        cpu_warning_threshold: float = 80.0,
        cpu_critical_threshold: float = 90.0,
        ram_warning_threshold: float = 85.0,
        ram_critical_threshold: float = 92.0,
        disk_warning_threshold: float = 85.0,
        disk_critical_threshold: float = 92.0,
        net_tx_warning_kbps: float = 30_000.0,  # ~30 MB/s
        net_rx_warning_kbps: float = 50_000.0,  # ~50 MB/s
        anomaly_score_threshold: float = 0.50,
    ) -> None:
        """Initialize the diagnostic engine with configurable operational thresholds."""
        self.cpu_warn = cpu_warning_threshold
        self.cpu_crit = cpu_critical_threshold
        self.ram_warn = ram_warning_threshold
        self.ram_crit = ram_critical_threshold
        self.disk_warn = disk_warning_threshold
        self.disk_crit = disk_critical_threshold
        self.net_tx_warn = net_tx_warning_kbps
        self.net_rx_warn = net_rx_warning_kbps
        self.anomaly_thresh = anomaly_score_threshold

    def generate_report(
        self,
        prediction: Optional[PredictionResult] = None,
        metrics: Optional[Union[SystemMetrics, SystemMetricRecord, dict[str, Any]]] = None,
        features: Optional[dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> DiagnosticReport:
        """Analyze current telemetry and ML outputs to build an evidence-based report.

        Args:
            prediction: Optional PredictionResult from PredictionService.
            metrics: Optional SystemMetrics, SystemMetricRecord, or raw metric dictionary.
            features: Optional engineered 39-feature vector dictionary.
            timestamp: Evaluation timestamp (UTC). Defaults to now.

        Returns:
            Populated DiagnosticReport containing prioritized recommendations.
        """
        ts = timestamp or (prediction.timestamp if prediction else datetime.now(timezone.utc))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Extract metric parameters safely
        cpu_pct = self._extract_float(metrics, "cpu_percent", features, "cpu_utilization_percent")
        ram_pct = self._extract_float(metrics, "memory_percent", features, "memory_utilization_percent")
        disk_pct = self._extract_float(metrics, "disk_percent", features, "disk_utilization_percent")
        disk_active_pct = self._extract_float(metrics, "disk_active_percent", features, "disk_active_percent")
        net_tx_kbps = self._extract_net_kbps(metrics, features, is_tx=True)
        net_rx_kbps = self._extract_net_kbps(metrics, features, is_tx=False)

        top_proc_name = self._extract_top_process_name(metrics)
        top_proc_cpu = self._extract_top_process_cpu(metrics)
        top_proc_ram = self._extract_top_process_ram(metrics)
        top_proc_pid = self._extract_top_process_pid(metrics)

        anom_score = prediction.anomaly_score if prediction else 0.0
        is_anom = prediction.is_anomaly if prediction else False
        health_score = prediction.health_score if prediction else None
        risk_cat = prediction.risk_category if prediction else RiskCategory.NORMAL

        recommendations: list[DiagnosticRecommendation] = []

        # ---------------------------------------------------------------------
        # Rule 1: CPU Saturation & Process Dominance
        # ---------------------------------------------------------------------
        if cpu_pct is not None and cpu_pct >= self.cpu_warn:
            is_crit = cpu_pct >= self.cpu_crit
            sev = EvidenceLevel.CRITICAL if is_crit else EvidenceLevel.HIGH
            ev_list: list[DiagnosticEvidence] = [
                DiagnosticEvidence(
                    metric_name="cpu_percent",
                    observed_value=f"{cpu_pct:.1f}%",
                    threshold=f">= {self.cpu_crit:.1f}% Critical (>= {self.cpu_warn:.1f}% Warning)",
                    level=sev,
                    description=f"Host CPU utilization ({cpu_pct:.1f}%) exceeds nominal headroom limit.",
                )
            ]

            remediation = [
                "Inspect live process hierarchy with 'top -c' / 'htop' or Windows Task Manager / Process Explorer.",
            ]

            if top_proc_name and top_proc_cpu is not None and top_proc_cpu >= 40.0:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="top_process_cpu_percent",
                        observed_value=f"{top_proc_cpu:.1f}% (Process: {top_proc_name}, PID: {top_proc_pid or 'N/A'})",
                        threshold=">= 40.0% Single Process CPU",
                        level=sev,
                        description=f"Process '{top_proc_name}' accounts for the vast majority of CPU consumption.",
                    )
                )
                hypothesis = (
                    f"Runaway thread, infinite compute loop, or intensive compute job in '{top_proc_name}' "
                    f"(PID: {top_proc_pid or 'N/A'}) consuming {top_proc_cpu:.1f}% CPU."
                )
                remediation.extend([
                    f"Check thread dumps or logs for PID {top_proc_pid or 'N/A'} ('{top_proc_name}') to pinpoint blocked loops.",
                    f"Throttle priority with 'renice' or issue a graceful termination signal (SIGTERM/SIGINT) to PID {top_proc_pid or 'N/A'}.",
                ])
                target = f"{top_proc_name} (PID {top_proc_pid})" if top_proc_pid else top_proc_name
            else:
                hypothesis = "Multi-process aggregate compute demand or high context-switching load across active cores."
                remediation.append("Review concurrency configuration, worker thread pools, or scale host compute resources.")
                target = "CPU Subsystem"

            remediation.append("Verify CPU throttling and core thermal dissipation if sustained above 95%.")

            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-CPU-001",
                    category=DiagnosticCategory.CPU,
                    severity=sev,
                    title=f"{'Severe' if is_crit else 'Elevated'} CPU Saturation ({cpu_pct:.1f}%)",
                    summary=f"System processor capacity is operating under {'critical' if is_crit else 'heavy'} compute pressure.",
                    root_cause_hypothesis=hypothesis,
                    evidence=ev_list,
                    remediation_steps=remediation,
                    target_component=target,
                )
            )

        # ---------------------------------------------------------------------
        # Rule 2: Memory Pressure & Exhaustion
        # ---------------------------------------------------------------------
        if ram_pct is not None and ram_pct >= self.ram_warn:
            is_crit = ram_pct >= self.ram_crit
            sev = EvidenceLevel.CRITICAL if is_crit else EvidenceLevel.HIGH
            ev_list = [
                DiagnosticEvidence(
                    metric_name="memory_percent",
                    observed_value=f"{ram_pct:.1f}%",
                    threshold=f">= {self.ram_crit:.1f}% Critical (>= {self.ram_warn:.1f}% Warning)",
                    level=sev,
                    description=f"Physical RAM utilization ({ram_pct:.1f}%) leaves minimal headroom, risking OOM kills.",
                )
            ]

            remediation = [
                "Review resident set size (RSS) allocations across application services.",
                "Inspect swap utilization to ensure page-thrashing is not degrading I/O performance.",
            ]

            if top_proc_name and top_proc_ram is not None and top_proc_ram >= 25.0:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="top_process_memory_percent",
                        observed_value=f"{top_proc_ram:.1f}% (Process: {top_proc_name})",
                        threshold=">= 25.0% Process Memory",
                        level=sev,
                        description=f"Process '{top_proc_name}' holds dominant share of system memory.",
                    )
                )
                hypothesis = (
                    f"Possible memory leak, unconstrained cache growth, or large in-memory dataset in '{top_proc_name}' "
                    f"consuming {top_proc_ram:.1f}% RAM."
                )
                remediation.insert(0, f"Inspect heap allocations and profile object lifecycles in '{top_proc_name}'.")
                remediation.append(f"Consider graceful restart or memory limit enforcement (cgroups/Docker limits) for '{top_proc_name}'.")
                target = f"{top_proc_name}"
            else:
                hypothesis = "General system-wide memory accumulation across multi-tenant applications or database buffers."
                target = "Memory (RAM)"

            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-MEM-001",
                    category=DiagnosticCategory.MEMORY,
                    severity=sev,
                    title=f"{'Critical' if is_crit else 'High'} Memory Utilization ({ram_pct:.1f}%)",
                    summary=f"Host RAM is nearing exhaustion ({ram_pct:.1f}%).",
                    root_cause_hypothesis=hypothesis,
                    evidence=ev_list,
                    remediation_steps=remediation,
                    target_component=target,
                )
            )

        # ---------------------------------------------------------------------
        # Rule 3: Storage Partition Saturation
        # ---------------------------------------------------------------------
        if disk_pct is not None and disk_pct >= self.disk_warn:
            is_crit = disk_pct >= self.disk_crit
            sev = EvidenceLevel.CRITICAL if is_crit else EvidenceLevel.HIGH
            ev_list = [
                DiagnosticEvidence(
                    metric_name="disk_percent",
                    observed_value=f"{disk_pct:.1f}%",
                    threshold=f">= {self.disk_crit:.1f}% Critical (>= {self.disk_warn:.1f}% Warning)",
                    level=sev,
                    description=f"Storage volume capacity ({disk_pct:.1f}%) is nearing full exhaustion.",
                )
            ]

            remediation = [
                "Locate large uncompressed files, rotated dumps, or log accumulation in /var/log, logs/, or temp folders.",
                "Execute log pruning or configure automated retention policy (e.g. SQLite retention purges).",
                "Expand physical volume capacity or provision additional block storage mount.",
            ]

            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-DISK-001",
                    category=DiagnosticCategory.DISK,
                    severity=sev,
                    title=f"{'Critical' if is_crit else 'Elevated'} Storage Volume Saturation ({disk_pct:.1f}%)",
                    summary=f"Filesystem storage capacity is severely restricted ({disk_pct:.1f}% used).",
                    root_cause_hypothesis="Rapid log accumulation, unrotated database growth, or temp artifacts consuming free partition blocks.",
                    evidence=ev_list,
                    remediation_steps=remediation,
                    target_component="Storage Filesystem",
                )
            )

        # ---------------------------------------------------------------------
        # Rule 3b: Physical Disk I/O Saturation & High Active Time
        # ---------------------------------------------------------------------
        if disk_active_pct is not None and disk_active_pct >= 85.0:
            is_crit = disk_active_pct >= 95.0
            sev = EvidenceLevel.CRITICAL if is_crit else EvidenceLevel.HIGH
            ev_list = [
                DiagnosticEvidence(
                    metric_name="disk_active_percent",
                    observed_value=f"{disk_active_pct:.1f}%",
                    threshold=">= 95.0% Critical (>= 85.0% Warning)",
                    level=sev,
                    description=f"Physical disk active time ({disk_active_pct:.1f}%) indicates severe disk I/O bottleneck.",
                )
            ]
            remediation = [
                "Identify high I/O processes using resource monitor or per-process I/O counters.",
                "Check for concurrent heavy database scans, unindexed queries, or large unbuffered writes.",
                "Consider upgrading to high-throughput SSD/NVMe or distributing I/O across separate spindles.",
            ]
            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-DISK-002",
                    category=DiagnosticCategory.DISK,
                    severity=sev,
                    title=f"{'Critical' if is_crit else 'High'} Disk I/O Saturation ({disk_active_pct:.1f}% Active)",
                    summary=f"Physical storage drive is operating under sustained I/O bottleneck ({disk_active_pct:.1f}% busy).",
                    root_cause_hypothesis="Excessive synchronous write bursts, heavy database queries, or concurrent disk I/O thrashing.",
                    evidence=ev_list,
                    remediation_steps=remediation,
                    target_component="Physical Disk",
                )
            )

        # ---------------------------------------------------------------------
        # Rule 4: Network Ingress/Egress Surge
        # ---------------------------------------------------------------------
        if (net_rx_kbps is not None and net_rx_kbps >= self.net_rx_warn) or (
            net_tx_kbps is not None and net_tx_kbps >= self.net_tx_warn
        ):
            ev_list = []
            if net_rx_kbps and net_rx_kbps >= self.net_rx_warn:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="network_rx_kbps",
                        observed_value=f"{net_rx_kbps:,.1f} KB/s ({(net_rx_kbps/1024):.1f} MB/s)",
                        threshold=f">= {self.net_rx_warn:,.0f} KB/s",
                        level=EvidenceLevel.HIGH,
                        description="Inbound network throughput exhibits an anomalous transmission rate spike.",
                    )
                )
            if net_tx_kbps and net_tx_kbps >= self.net_tx_warn:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="network_tx_kbps",
                        observed_value=f"{net_tx_kbps:,.1f} KB/s ({(net_tx_kbps/1024):.1f} MB/s)",
                        threshold=f">= {self.net_tx_warn:,.0f} KB/s",
                        level=EvidenceLevel.HIGH,
                        description="Outbound network throughput exceeds nominal steady-state baseline.",
                    )
                )

            remediation = [
                "Inspect active network connections and socket counts via 'netstat -tulnp' or 'ss -s'.",
                "Verify whether network traffic corresponds to an intended backup, batch ETL sync, or external ingress burst.",
                "Apply rate-limiting or ingress firewall traffic rules if traffic appears unauthenticated.",
            ]

            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-NET-001",
                    category=DiagnosticCategory.NETWORK,
                    severity=EvidenceLevel.HIGH,
                    title="Anomalous Network Throughput Surge",
                    summary="Network I/O throughput is significantly elevated compared to nominal server baselines.",
                    root_cause_hypothesis="Data synchronization loop, unthrottled backup transfer, ingress traffic storm, or high client connection concurrency.",
                    evidence=ev_list,
                    remediation_steps=remediation,
                    target_component="Network Interface",
                )
            )

        # ---------------------------------------------------------------------
        # Rule 5: Isolation Forest Statistical Outlier
        # ---------------------------------------------------------------------
        if is_anom or anom_score >= self.anomaly_thresh:
            sev = EvidenceLevel.CRITICAL if anom_score >= 0.75 else EvidenceLevel.HIGH
            ev_list = [
                DiagnosticEvidence(
                    metric_name="anomaly_score",
                    observed_value=f"{anom_score:.4f}",
                    threshold=f">= {self.anomaly_thresh:.2f} Decision Boundary",
                    level=sev,
                    description=f"Isolation Forest estimator scored sample as a statistical outlier ({anom_score:.4f}).",
                ),
            ]
            if prediction:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="raw_decision_score",
                        observed_value=f"{prediction.raw_decision_score:.4f}",
                        threshold="< 0.0 Outlier Region",
                        level=sev,
                        description=f"Negative raw decision score ({prediction.raw_decision_score:.4f}) confirms divergence from baseline training cluster.",
                    )
                )

            remediation = [
                "Correlate observation timestamp with recent software releases, pipeline migrations, or cron schedules.",
                "Inspect the 39-feature vector audit log to isolate which multivariate dimensions deviated most sharply.",
                "Validate model training status: ensure model artifact was trained on representative steady-state telemetry.",
            ]

            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-ML-001",
                    category=DiagnosticCategory.ANOMALY,
                    severity=sev,
                    title="Isolation Forest Multivariate Behavioral Anomaly",
                    summary=f"Machine learning model identified a statistically significant behavioral deviation (score: {anom_score:.4f}).",
                    root_cause_hypothesis="Multivariate telemetry correlation divergent from the normal operational distribution modeled during training.",
                    evidence=ev_list,
                    remediation_steps=remediation,
                    target_component=prediction.model_name if prediction else "Isolation Forest Model",
                )
            )

        # ---------------------------------------------------------------------
        # Rule 6: Nominal Baseline (if no issues detected)
        # ---------------------------------------------------------------------
        if not recommendations:
            ev_list = []
            if cpu_pct is not None:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="cpu_percent",
                        observed_value=f"{cpu_pct:.1f}%",
                        threshold=f"< {self.cpu_warn:.1f}%",
                        level=EvidenceLevel.INFO,
                        description="CPU utilization is operating comfortably within nominal bounds.",
                    )
                )
            if ram_pct is not None:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="memory_percent",
                        observed_value=f"{ram_pct:.1f}%",
                        threshold=f"< {self.ram_warn:.1f}%",
                        level=EvidenceLevel.INFO,
                        description="Physical memory utilization indicates sufficient free allocation buffer.",
                    )
                )
            if disk_pct is not None:
                ev_list.append(
                    DiagnosticEvidence(
                        metric_name="disk_percent",
                        observed_value=f"{disk_pct:.1f}%",
                        threshold=f"< {self.disk_warn:.1f}%",
                        level=EvidenceLevel.INFO,
                        description="Filesystem capacity maintains healthy storage headroom.",
                    )
                )

            recommendations.append(
                DiagnosticRecommendation(
                    id="DIAG-NOM-001",
                    category=DiagnosticCategory.SYSTEM,
                    severity=EvidenceLevel.INFO,
                    title="System Operating Within Nominal Operational Parameters",
                    summary="All monitored telemetry domains (CPU, RAM, Disk, Network) and ML estimators reflect healthy state.",
                    root_cause_hypothesis="Steady-state balanced server operation matching historical baselines.",
                    evidence=ev_list,
                    remediation_steps=[
                        "No remediation actions currently required.",
                        "Maintain routine automated metric ingestion and periodic model re-training cycles.",
                    ],
                    target_component="All Subsystems",
                )
            )

        # Sort recommendations by severity priority: CRITICAL -> HIGH -> MODERATE -> LOW -> INFO
        severity_order = {
            EvidenceLevel.CRITICAL: 0,
            EvidenceLevel.HIGH: 1,
            EvidenceLevel.MODERATE: 2,
            EvidenceLevel.LOW: 3,
            EvidenceLevel.INFO: 4,
        }
        recommendations.sort(key=lambda r: severity_order.get(r.severity, 99))

        crit_count = sum(1 for r in recommendations if r.severity == EvidenceLevel.CRITICAL)
        warn_count = sum(1 for r in recommendations if r.severity in (EvidenceLevel.HIGH, EvidenceLevel.MODERATE))

        if crit_count > 0:
            headline = f"⚠️ {crit_count} Critical Operational Finding{'s' if crit_count > 1 else ''} Require Immediate Attention"
            primary = recommendations[0].title
        elif warn_count > 0:
            headline = f"⚡ {warn_count} Warning Finding{'s' if warn_count > 1 else ''} Identified"
            primary = recommendations[0].title
        else:
            headline = "🟢 All Telemetry Indicators Nominal — No Immediate Action Required"
            primary = "None"

        return DiagnosticReport(
            timestamp=ts,
            overall_health_score=health_score,
            risk_category=risk_cat,
            anomaly_score=anom_score,
            is_anomaly=is_anom,
            recommendations=recommendations,
            summary_headline=headline,
            primary_concern=primary,
            critical_count=crit_count,
            warning_count=warn_count,
        )

    # -------------------------------------------------------------------------
    # Metric Extraction Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _extract_float(
        metrics: Any,
        metric_attr: str,
        features: Optional[dict[str, Any]],
        feat_name: str,
    ) -> Optional[float]:
        """Extract a floating-point metric value from metrics or feature dictionary."""
        if metrics is not None:
            if hasattr(metrics, metric_attr):
                val = getattr(metrics, metric_attr)
                if val is not None:
                    return float(val)
            elif isinstance(metrics, dict) and metric_attr in metrics and metrics[metric_attr] is not None:
                return float(metrics[metric_attr])
            elif hasattr(metrics, "cpu") and metric_attr == "cpu_percent" and metrics.cpu is not None:
                return float(metrics.cpu.utilization_percent)
            elif hasattr(metrics, "memory") and metric_attr == "memory_percent" and metrics.memory is not None:
                return float(metrics.memory.utilization_percent)
            elif hasattr(metrics, "disk") and metric_attr == "disk_percent" and metrics.disk is not None:
                return float(metrics.disk.utilization_percent)
            elif hasattr(metrics, "disk") and metric_attr == "disk_active_percent" and metrics.disk is not None:
                if metrics.disk.active_time_percent is not None:
                    return float(metrics.disk.active_time_percent)

        if features and feat_name in features and features[feat_name] is not None:
            return float(features[feat_name])
        return None

    @staticmethod
    def _extract_net_kbps(metrics: Any, features: Optional[dict[str, Any]], is_tx: bool) -> Optional[float]:
        """Extract network throughput in KB/s."""
        attr = "network_bytes_sent_per_sec" if is_tx else "network_bytes_recv_per_sec"
        feat = "network_bytes_sent_per_sec" if is_tx else "network_bytes_recv_per_sec"

        if metrics is not None:
            if hasattr(metrics, "network") and metrics.network is not None:
                bps = metrics.network.bytes_sent_per_sec if is_tx else metrics.network.bytes_recv_per_sec
                return float(bps) / 1024.0
            if hasattr(metrics, attr):
                bps = getattr(metrics, attr)
                if bps is not None:
                    return float(bps) / 1024.0

        if features and feat in features and features[feat] is not None:
            return float(features[feat]) / 1024.0
        return None

    @staticmethod
    def _extract_top_process_name(metrics: Any) -> Optional[str]:
        if metrics is None:
            return None
        if hasattr(metrics, "top_process_name") and metrics.top_process_name:
            return str(metrics.top_process_name)
        if isinstance(metrics, dict) and "top_process_name" in metrics and metrics["top_process_name"]:
            return str(metrics["top_process_name"])
        if hasattr(metrics, "processes") and metrics.processes:
            top_p = max(metrics.processes, key=lambda p: getattr(p, "cpu_percent", 0.0))
            return getattr(top_p, "name", None)
        return None

    @staticmethod
    def _extract_top_process_cpu(metrics: Any) -> Optional[float]:
        if metrics is None:
            return None
        if hasattr(metrics, "top_process_cpu_percent") and metrics.top_process_cpu_percent is not None:
            return float(metrics.top_process_cpu_percent)
        if isinstance(metrics, dict) and "top_process_cpu_percent" in metrics and metrics["top_process_cpu_percent"] is not None:
            return float(metrics["top_process_cpu_percent"])
        if hasattr(metrics, "processes") and metrics.processes:
            top_p = max(metrics.processes, key=lambda p: getattr(p, "cpu_percent", 0.0))
            return float(getattr(top_p, "cpu_percent", 0.0))
        return None

    @staticmethod
    def _extract_top_process_ram(metrics: Any) -> Optional[float]:
        if metrics is None:
            return None
        if hasattr(metrics, "top_process_memory_percent") and metrics.top_process_memory_percent is not None:
            return float(metrics.top_process_memory_percent)
        if isinstance(metrics, dict) and "top_process_memory_percent" in metrics and metrics["top_process_memory_percent"] is not None:
            return float(metrics["top_process_memory_percent"])
        if hasattr(metrics, "processes") and metrics.processes:
            top_p = max(metrics.processes, key=lambda p: getattr(p, "memory_percent", 0.0))
            return float(getattr(top_p, "memory_percent", 0.0))
        return None

    @staticmethod
    def _extract_top_process_pid(metrics: Any) -> Optional[int]:
        if metrics is None:
            return None
        if hasattr(metrics, "top_process_pid") and metrics.top_process_pid is not None:
            return int(metrics.top_process_pid)
        if isinstance(metrics, dict) and "top_process_pid" in metrics and metrics["top_process_pid"] is not None:
            return int(metrics["top_process_pid"])
        if hasattr(metrics, "processes") and metrics.processes:
            top_p = max(metrics.processes, key=lambda p: getattr(p, "cpu_percent", 0.0))
            return getattr(top_p, "pid", None)
        return None

