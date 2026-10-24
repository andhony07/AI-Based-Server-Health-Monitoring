"""Dashboard integration service coordinator.

Coordinates data access from SQLite persistence, telemetry collection,
and machine learning inference for Streamlit visualization views.
"""

from __future__ import annotations

import csv
import io
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Union

from app.collectors.system_collector import SystemCollector
from app.core.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.database.connection import get_connection
from app.database.models import (
    FeatureVectorRecord,
    PersistenceResult,
    SystemMetricRecord,
    ValidationLogRecord,
    parse_utc_timestamp,
)
from app.database.schema import FEATURE_COLUMNS
from app.database.service import PersistenceService
from app.ml.diagnostics import DiagnosticEngine, DiagnosticReport
from app.ml.models import PredictionResult, RiskCategory
from app.ml.prediction_service import PredictionService
from app.ml.simulation import (
    DeterministicAnomalySimulator,
    SCENARIO_PROFILES,
    ScenarioProfile,
    SimulationResult,
    SimulationScenario,
)
from app.models.metrics import SystemMetrics
from app.preprocessing.pipeline import PreprocessingPipeline, ProcessedTelemetry

logger = get_logger("app.dashboard.service")


class DashboardService:
    """Central service coordinator for all dashboard data retrieval and actions."""

    _background_thread: Optional[threading.Thread] = None
    _stop_event: threading.Event = threading.Event()
    _thread_lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        settings: Optional[Settings] = None,
        persistence_service: Optional[PersistenceService] = None,
        prediction_service: Optional[PredictionService] = None,
        collector: Optional[SystemCollector] = None,
        pipeline: Optional[PreprocessingPipeline] = None,
        simulator: Optional[DeterministicAnomalySimulator] = None,
        diagnostic_engine: Optional[DiagnosticEngine] = None,
    ) -> None:
        """Initialize the dashboard service.

        Args:
            settings: Optional custom Settings instance.
            persistence_service: Optional custom PersistenceService.
            prediction_service: Optional custom PredictionService.
            collector: Optional custom SystemCollector.
            pipeline: Optional custom PreprocessingPipeline.
            simulator: Optional DeterministicAnomalySimulator instance.
            diagnostic_engine: Optional DiagnosticEngine instance.
        """
        self.settings: Settings = settings or get_settings()
        self.persistence: PersistenceService = (
            persistence_service or PersistenceService(settings=self.settings)
        )
        self.prediction_service: PredictionService = (
            prediction_service or PredictionService(settings=self.settings)
        )
        self.collector: SystemCollector = collector or SystemCollector(settings=self.settings)
        self.pipeline: PreprocessingPipeline = (
            pipeline or PreprocessingPipeline(settings=self.settings)
        )
        self.simulator: DeterministicAnomalySimulator = (
            simulator or DeterministicAnomalySimulator()
        )
        self.diagnostic_engine: DiagnosticEngine = (
            diagnostic_engine or DiagnosticEngine()
        )

    # -------------------------------------------------------------------------
    # Latest Data Access
    # -------------------------------------------------------------------------

    def get_latest_metrics(self) -> Optional[SystemMetricRecord]:
        """Fetch the most recent system metrics record from SQLite.

        Returns:
            Latest SystemMetricRecord or None if no records exist or on DB error.
        """
        try:
            records = self.persistence.get_latest_metrics(limit=1)
            return records[0] if records else None
        except Exception as exc:
            logger.warning("Could not retrieve latest metrics from database: %s", exc)
            return None

    def get_latest_feature_vector(self) -> Optional[FeatureVectorRecord]:
        """Fetch the most recent engineered feature vector record.

        Returns:
            Latest FeatureVectorRecord or None.
        """
        try:
            records = self.persistence.get_latest_features(limit=1)
            return records[0] if records else None
        except Exception as exc:
            logger.warning("Could not retrieve latest features from database: %s", exc)
            return None

    def get_latest_prediction(self) -> Optional[PredictionResult]:
        """Evaluate and return ML health and risk predictions for the latest feature record.

        Returns:
            Populated PredictionResult or None if no feature vector is available.
        """
        latest_feat = self.get_latest_feature_vector()
        if latest_feat is None:
            return None

        try:
            return self.prediction_service.predict(latest_feat.features)
        except Exception as exc:
            logger.warning("Failed to evaluate prediction on latest feature vector: %s", exc)
            return None

    # -------------------------------------------------------------------------
    # Live Telemetry Snapshot & Background Worker
    # -------------------------------------------------------------------------

    def capture_live_snapshot(
        self,
        persist: bool = True,
    ) -> tuple[Optional[SystemMetricRecord], Optional[PredictionResult], Optional[str]]:
        """Collect a live telemetry sample, process features, optionally persist, and predict.

        Args:
            persist: If True, atomically saves sample into SQLite.

        Returns:
            Tuple of (latest_metric_record, prediction_result, error_message).
        """
        try:
            metrics = self.collector.collect()
            processed = self.pipeline.process(metrics)

            if persist:
                persist_res = self.persistence.persist_sample(metrics, processed)
                if not persist_res.success:
                    logger.warning("Persistence warning during snapshot: %s", persist_res.error_message)

            prediction = self.prediction_service.predict(processed)

            # Retrieve persisted record if available, else build record from metrics
            latest_record = self.get_latest_metrics()
            if latest_record is None:
                # If database empty or not persisted, map current sample to record format
                top_p = max(metrics.processes, key=lambda p: p.cpu_percent) if metrics.processes else None
                latest_record = SystemMetricRecord(
                    id=0,
                    timestamp=metrics.timestamp,
                    cpu_percent=metrics.cpu.utilization_percent if metrics.cpu else None,
                    cpu_logical_cores=metrics.cpu.logical_cores if metrics.cpu else None,
                    cpu_physical_cores=metrics.cpu.physical_cores if metrics.cpu else None,
                    memory_total_bytes=metrics.memory.total_bytes if metrics.memory else None,
                    memory_used_bytes=metrics.memory.used_bytes if metrics.memory else None,
                    memory_available_bytes=metrics.memory.available_bytes if metrics.memory else None,
                    memory_percent=metrics.memory.utilization_percent if metrics.memory else None,
                    disk_total_bytes=metrics.disk.total_bytes if metrics.disk else None,
                    disk_used_bytes=metrics.disk.used_bytes if metrics.disk else None,
                    disk_free_bytes=metrics.disk.free_bytes if metrics.disk else None,
                    disk_percent=metrics.disk.utilization_percent if metrics.disk else None,
                    disk_active_percent=metrics.disk.active_time_percent if metrics.disk else None,
                    disk_read_bytes_per_sec=metrics.disk.read_bytes_per_sec if metrics.disk else None,
                    disk_write_bytes_per_sec=metrics.disk.write_bytes_per_sec if metrics.disk else None,
                    network_bytes_sent=metrics.network.bytes_sent if metrics.network else None,
                    network_bytes_recv=metrics.network.bytes_recv if metrics.network else None,
                    network_bytes_sent_per_sec=metrics.network.upload_kbps * 1024.0 if metrics.network else None,
                    network_bytes_recv_per_sec=metrics.network.download_kbps * 1024.0 if metrics.network else None,
                    process_count=len(metrics.processes),
                    top_process_pid=top_p.pid if top_p else None,
                    top_process_name=top_p.name if top_p else None,
                    top_process_cpu_percent=top_p.cpu_percent if top_p else None,
                    top_process_memory_percent=top_p.memory_percent if top_p else None,
                )

            return latest_record, prediction, None
        except Exception as exc:
            logger.error("Failed to capture live telemetry snapshot: %s", exc, exc_info=True)
            return None, None, str(exc)

    def is_background_monitoring_running(self) -> bool:
        """Check if background telemetry collection thread is active."""
        with self._thread_lock:
            return (
                self._background_thread is not None
                and self._background_thread.is_alive()
                and not self._stop_event.is_set()
            )

    def start_background_monitoring(self, interval: Optional[float] = None) -> bool:
        """Start a managed background thread collecting and persisting telemetry.

        Args:
            interval: Optional sample interval in seconds. Defaults to config setting.

        Returns:
            True if started, False if already running.
        """
        with self._thread_lock:
            if self._background_thread is not None and self._background_thread.is_alive():
                logger.info("Background monitoring thread is already running.")
                return False

            self._stop_event.clear()
            sample_interval = interval or self.settings.metric_collection_interval

            def _monitoring_worker() -> None:
                logger.info("Background monitoring thread started (interval=%.1fs).", sample_interval)
                while not self._stop_event.is_set():
                    try:
                        metrics = self.collector.collect()
                        processed = self.pipeline.process(metrics)
                        self.persistence.persist_sample(metrics, processed)
                    except Exception as err:
                        logger.warning("Error in background monitoring iteration: %s", err)
                    self._stop_event.wait(timeout=sample_interval)
                logger.info("Background monitoring thread exited cleanly.")

            thread = threading.Thread(
                target=_monitoring_worker,
                name="DashboardTelemetryWorker",
                daemon=True,
            )
            thread.start()
            self._background_thread = thread
            return True

    def stop_background_monitoring(self, timeout: float = 3.0) -> bool:
        """Stop the background telemetry collection worker safely.

        Args:
            timeout: Maximum seconds to wait for thread termination.

        Returns:
            True if stopped or already inactive.
        """
        with self._thread_lock:
            if self._background_thread is None or not self._background_thread.is_alive():
                return True

            self._stop_event.set()
            self._background_thread.join(timeout=timeout)
            is_stopped = not self._background_thread.is_alive()
            if is_stopped:
                self._background_thread = None
            return is_stopped

    # -------------------------------------------------------------------------
    # Historical Queries
    # -------------------------------------------------------------------------

    def get_historical_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[SystemMetricRecord]:
        """Fetch historical system metrics within an optional time range or latest-N.

        Args:
            start_time: Optional start timestamp (UTC).
            end_time: Optional end timestamp (UTC).
            limit: Maximum count of rows to return.

        Returns:
            List of SystemMetricRecord instances ordered chronologically.
        """
        try:
            if start_time is not None and end_time is not None:
                records = self.persistence.get_metrics_range(start_time, end_time)
                return records[:limit]
            # Retrieve latest N and sort chronologically for charts
            records = self.persistence.get_latest_metrics(limit=limit)
            return sorted(records, key=lambda r: r.timestamp)
        except Exception as exc:
            logger.warning("Failed to retrieve historical metrics: %s", exc)
            return []

    def get_historical_features(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> list[FeatureVectorRecord]:
        """Fetch historical feature vector records.

        Args:
            start_time: Optional start timestamp (UTC).
            end_time: Optional end timestamp (UTC).
            limit: Maximum count to return.

        Returns:
            List of FeatureVectorRecord instances ordered chronologically.
        """
        try:
            if start_time is not None and end_time is not None:
                records = self.persistence.get_features_range(start_time, end_time)
                return records[:limit]
            records = self.persistence.get_latest_features(limit=limit)
            return sorted(records, key=lambda r: r.timestamp)
        except Exception as exc:
            logger.warning("Failed to retrieve historical features: %s", exc)
            return []

    def get_historical_anomalies(
        self,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Evaluate recent historical feature vectors and correlate with raw telemetry.

        Distinguishes between trained model inferences and heuristic baseline scores.

        Args:
            limit: Maximum number of recent feature vectors to evaluate.

        Returns:
            List of structured anomaly dictionaries.
        """
        try:
            features = self.get_historical_features(limit=limit)
            if not features:
                return []

            # Create lookup map of raw metrics by ID for metric correlation
            metric_ids = [f.metric_id for f in features if f.metric_id is not None]
            metrics = self.get_historical_metrics(limit=limit)
            metric_lookup = {m.id: m for m in metrics}

            results: list[dict[str, Any]] = []
            for feat in features:
                pred = self.prediction_service.predict(feat.features)
                m = metric_lookup.get(feat.metric_id) if feat.metric_id else None

                results.append(
                    {
                        "feature_id": feat.id,
                        "metric_id": feat.metric_id,
                        "timestamp": feat.timestamp,
                        "anomaly_score": pred.anomaly_score,
                        "is_anomaly": pred.is_anomaly,
                        "health_score": pred.health_score,
                        "risk_category": pred.risk_category.value,
                        "model_name": pred.model_name,
                        "is_trained_model": self.prediction_service.is_model_ready(),
                        "cpu_percent": m.cpu_percent if m else feat.features.get("cpu_utilization_percent"),
                        "memory_percent": m.memory_percent if m else feat.features.get("memory_utilization_percent"),
                        "disk_percent": m.disk_percent if m else feat.features.get("disk_utilization_percent"),
                        "network_kbps": (
                            (m.network_bytes_sent_per_sec or 0.0) + (m.network_bytes_recv_per_sec or 0.0)
                        ) / 1024.0 if m else 0.0,
                    }
                )

            return sorted(results, key=lambda x: x["timestamp"], reverse=True)
        except Exception as exc:
            logger.warning("Failed to compute historical anomalies: %s", exc)
            return []

    # -------------------------------------------------------------------------
    # Database Summary & Inspection
    # -------------------------------------------------------------------------

    def get_database_summary(self) -> dict[str, Any]:
        """Inspect the SQLite database state, record counts, and timestamp ranges.

        Returns:
            Dictionary containing table counts, file size, paths, and date ranges.
        """
        db_path = self.persistence.db_path
        exists = db_path.exists()
        file_size_bytes = db_path.stat().st_size if exists else 0

        counts = {
            "system_metrics": 0,
            "feature_vectors": 0,
            "validation_logs": 0,
            "schema_migrations": 0,
        }
        earliest_time: Optional[datetime] = None
        latest_time: Optional[datetime] = None

        if exists:
            try:
                counts = self.persistence.get_record_counts()
                with get_connection(db_path, timeout=5.0) as conn:
                    cur_range = conn.execute(
                        "SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts FROM system_metrics;"
                    )
                    row = cur_range.fetchone()
                    if row and row["min_ts"]:
                        earliest_time = parse_utc_timestamp(row["min_ts"])
                        latest_time = parse_utc_timestamp(row["max_ts"])
            except Exception as exc:
                logger.warning("Error inspecting database summary: %s", exc)

        return {
            "database_path": str(db_path),
            "database_exists": exists,
            "file_size_bytes": file_size_bytes,
            "counts": counts,
            "total_records": sum(counts.values()),
            "earliest_timestamp": earliest_time,
            "latest_timestamp": latest_time,
            "retention_days": self.settings.db_retention_days,
        }

    def get_recent_validation_logs(self, limit: int = 50) -> list[ValidationLogRecord]:
        """Fetch recent preprocessing validation audit records.

        Args:
            limit: Maximum count to return.

        Returns:
            List of ValidationLogRecord instances.
        """
        try:
            return self.persistence.get_latest_validation_logs(limit=limit)
        except Exception as exc:
            logger.warning("Could not retrieve validation logs: %s", exc)
            return []

    # -------------------------------------------------------------------------
    # Anomaly Simulation & Diagnostic Integration
    # -------------------------------------------------------------------------

    def run_simulation(
        self,
        scenario: Union[SimulationScenario, str],
        persist: bool = False,
        seed: int = 42,
        **kwargs: Any,
    ) -> tuple[SimulationResult, DiagnosticReport]:
        """Execute a deterministic anomaly simulation through the full ML pipeline.

        Args:
            scenario: Simulation scenario enum or string key.
            persist: If True, commits the sample to the SQLite database.
            seed: Deterministic integer seed.
            **kwargs: Metric parameter overrides.

        Returns:
            Tuple of (SimulationResult, DiagnosticReport).
        """
        sim_res = self.simulator.simulate(
            scenario=scenario,
            pipeline=self.pipeline,
            prediction_service=self.prediction_service,
            persistence_service=self.persistence if persist else None,
            persist=persist,
            seed=seed,
            **kwargs,
        )
        diag_report = self.diagnostic_engine.generate_report(
            prediction=sim_res.prediction,
            metrics=sim_res.metrics,
            features=sim_res.processed.feature_vector.features,
            timestamp=sim_res.metrics.timestamp,
        )
        return sim_res, diag_report

    def get_diagnostics_for_latest(self) -> Optional[DiagnosticReport]:
        """Evaluate explainable diagnostic recommendations on the latest system telemetry.

        Returns:
            DiagnosticReport or None if no telemetry data exists.
        """
        latest_metric = self.get_latest_metrics()
        latest_feat = self.get_latest_feature_vector()
        latest_pred = self.get_latest_prediction()
        if latest_metric is None and latest_pred is None:
            return None

        return self.diagnostic_engine.generate_report(
            prediction=latest_pred,
            metrics=latest_metric,
            features=latest_feat.features if latest_feat else None,
            timestamp=latest_pred.timestamp if latest_pred else (latest_metric.timestamp if latest_metric else None),
        )

    # -------------------------------------------------------------------------
    # Operational Status Checks
    # -------------------------------------------------------------------------

    def get_operational_status(self) -> dict[str, Any]:
        """Execute non-destructive operational status checks across all monitoring subsystems.

        Returns:
            Structured operational health dictionary with status indicators and details.
        """
        db_path = self.persistence.db_path
        db_exists = db_path.exists()
        db_integrity = "unknown"
        db_err = None

        if db_exists:
            try:
                with get_connection(db_path, timeout=3.0) as conn:
                    cur = conn.execute("PRAGMA quick_check;")
                    row = cur.fetchone()
                    db_integrity = row[0] if row else "unknown"
            except Exception as exc:
                db_integrity = "error"
                db_err = str(exc)

        # 1. Database Subsystem
        counts = self.persistence.get_record_counts() if db_exists and db_integrity == "ok" else {}
        db_status = "OPERATIONAL" if (db_exists and db_integrity == "ok") else ("DEGRADED" if db_exists else "ERROR")

        # 2. ML Engine Subsystem
        is_model_ready = self.prediction_service.is_model_ready()
        ml_status = "OPERATIONAL" if is_model_ready else "FALLBACK"
        ml_details = {
            "status": ml_status,
            "model_name": self.prediction_service.model_name,
            "is_trained": is_model_ready,
            "expected_features": 39,
            "mode": "Trained Isolation Forest" if is_model_ready else "Deterministic Heuristic Baseline",
        }

        # 3. Collector Subsystem
        collector_ok = True
        collector_err = None
        try:
            # Check basic collector availability safely
            import psutil
            psutil.cpu_percent(interval=0.0)
            psutil.virtual_memory()
        except Exception as exc:
            collector_ok = False
            collector_err = str(exc)
        collector_status = "OPERATIONAL" if collector_ok else "ERROR"

        # 4. Background Monitoring Worker
        bg_running = self.is_background_monitoring_running()
        worker_status = "ACTIVE" if bg_running else "IDLE"

        # 5. Telemetry Freshness
        latest = self.get_latest_metrics()
        now_utc = datetime.now(timezone.utc)
        freshness_status = "NO_DATA"
        seconds_ago: Optional[float] = None

        if latest and latest.timestamp:
            ts = latest.timestamp if latest.timestamp.tzinfo is not None else latest.timestamp.replace(tzinfo=timezone.utc)
            seconds_ago = max(0.0, (now_utc - ts).total_seconds())
            if seconds_ago < 60.0:
                freshness_status = "FRESH"
            elif seconds_ago < 300.0:
                freshness_status = "WARM"
            else:
                freshness_status = "STALE"

        # Aggregate Overall System Operational State
        if db_status == "ERROR" or collector_status == "ERROR":
            overall = "CRITICAL"
            color = "#EF4444"
            headline = "One or more critical subsystems encountered an operational error."
        elif ml_status == "FALLBACK" or freshness_status in ("STALE", "NO_DATA"):
            overall = "DEGRADED"
            color = "#F59E0B"
            headline = "System is operational with warnings (heuristic ML baseline or stale telemetry)."
        else:
            overall = "HEALTHY"
            color = "#10B981"
            headline = "All platform subsystems (SQLite, ML engine, collectors, telemetry) operational."

        return {
            "timestamp": now_utc.isoformat(),
            "overall_status": overall,
            "status_color": color,
            "headline": headline,
            "subsystems": {
                "database": {
                    "status": db_status,
                    "path": str(db_path),
                    "exists": db_exists,
                    "integrity": db_integrity,
                    "error": db_err,
                    "telemetry_rows": counts.get("system_metrics", 0),
                    "feature_rows": counts.get("feature_vectors", 0),
                    "validation_rows": counts.get("validation_logs", 0),
                },
                "ml_engine": ml_details,
                "collector": {
                    "status": collector_status,
                    "error": collector_err,
                    "domains": ["CPU", "Memory", "Disk", "Network", "Processes"],
                },
                "background_worker": {
                    "status": worker_status,
                    "is_running": bg_running,
                },
                "telemetry_freshness": {
                    "status": freshness_status,
                    "latest_timestamp": latest.timestamp.isoformat() if latest else None,
                    "seconds_since_last_sample": round(seconds_ago, 1) if seconds_ago is not None else None,
                },
            },
        }

    # -------------------------------------------------------------------------
    # CSV Telemetry & Anomaly Export
    # -------------------------------------------------------------------------

    def export_metrics_csv(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> str:
        """Export historical system telemetry records as an RFC-4180 compliant CSV string.

        Args:
            start_time: Optional UTC start filter.
            end_time: Optional UTC end filter.
            limit: Maximum count of rows to return.

        Returns:
            CSV formatted text string.
        """
        records = self.get_historical_metrics(start_time=start_time, end_time=end_time, limit=limit)
        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "id",
            "timestamp_utc",
            "cpu_percent",
            "cpu_logical_cores",
            "memory_percent",
            "memory_used_mb",
            "memory_available_mb",
            "memory_total_mb",
            "disk_percent",
            "disk_active_percent",
            "disk_read_bytes_per_sec",
            "disk_write_bytes_per_sec",
            "disk_used_gb",
            "disk_free_gb",
            "disk_total_gb",
            "network_bytes_sent_per_sec",
            "network_bytes_recv_per_sec",
            "process_count",
            "top_process_name",
            "top_process_pid",
            "top_process_cpu_percent",
            "top_process_memory_percent",
        ]
        writer.writerow(headers)

        for r in records:
            writer.writerow([
                r.id,
                r.timestamp.isoformat() if r.timestamp else "",
                r.cpu_percent if r.cpu_percent is not None else "",
                r.cpu_logical_cores if r.cpu_logical_cores is not None else "",
                r.memory_percent if r.memory_percent is not None else "",
                round(r.memory_used_bytes / (1024 * 1024), 2) if r.memory_used_bytes else "",
                round(r.memory_available_bytes / (1024 * 1024), 2) if r.memory_available_bytes else "",
                round(r.memory_total_bytes / (1024 * 1024), 2) if r.memory_total_bytes else "",
                r.disk_percent if r.disk_percent is not None else "",
                r.disk_active_percent if r.disk_active_percent is not None else "",
                r.disk_read_bytes_per_sec if r.disk_read_bytes_per_sec is not None else "",
                r.disk_write_bytes_per_sec if r.disk_write_bytes_per_sec is not None else "",
                round(r.disk_used_bytes / (1024**3), 2) if r.disk_used_bytes else "",
                round(r.disk_free_bytes / (1024**3), 2) if r.disk_free_bytes else "",
                round(r.disk_total_bytes / (1024**3), 2) if r.disk_total_bytes else "",
                r.network_bytes_sent_per_sec if r.network_bytes_sent_per_sec is not None else "",
                r.network_bytes_recv_per_sec if r.network_bytes_recv_per_sec is not None else "",
                r.process_count if r.process_count is not None else "",
                r.top_process_name or "",
                r.top_process_pid or "",
                r.top_process_cpu_percent if r.top_process_cpu_percent is not None else "",
                r.top_process_memory_percent if r.top_process_memory_percent is not None else "",
            ])

        return output.getvalue()

    def export_anomalies_csv(
        self,
        limit: int = 500,
        filter_anomalies_only: bool = False,
    ) -> str:
        """Export evaluated historical anomaly and risk audit logs as CSV.

        Args:
            limit: Maximum count of rows to return.
            filter_anomalies_only: If True, filters strictly to samples where is_anomaly is True.

        Returns:
            CSV formatted text string.
        """
        anomalies = self.get_historical_anomalies(limit=limit)
        if filter_anomalies_only:
            anomalies = [a for a in anomalies if a.get("is_anomaly", False)]

        output = io.StringIO()
        writer = csv.writer(output)

        headers = [
            "timestamp_utc",
            "anomaly_score",
            "is_anomaly",
            "risk_category",
            "health_score",
            "cpu_percent",
            "memory_percent",
            "disk_percent",
            "network_kbps",
            "model_name",
            "is_trained_model",
        ]
        writer.writerow(headers)

        for a in anomalies:
            writer.writerow([
                a["timestamp"].isoformat() if isinstance(a["timestamp"], datetime) else str(a["timestamp"]),
                f"{a['anomaly_score']:.4f}",
                "TRUE" if a.get("is_anomaly") else "FALSE",
                a.get("risk_category", ""),
                f"{a['health_score']:.2f}" if a.get("health_score") is not None else "",
                f"{a.get('cpu_percent', 0.0):.1f}" if a.get("cpu_percent") is not None else "",
                f"{a.get('memory_percent', 0.0):.1f}" if a.get("memory_percent") is not None else "",
                f"{a.get('disk_percent', 0.0):.1f}" if a.get("disk_percent") is not None else "",
                f"{a.get('network_kbps', 0.0):.1f}" if a.get("network_kbps") is not None else "",
                a.get("model_name", ""),
                "TRUE" if a.get("is_trained_model") else "FALSE",
            ])

        return output.getvalue()

    def export_features_csv(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
    ) -> str:
        """Export 39-feature vectors as an RFC-4180 CSV string.

        Args:
            start_time: Optional UTC start filter.
            end_time: Optional UTC end filter.
            limit: Maximum count of records.

        Returns:
            CSV formatted text string.
        """
        features = self.get_historical_features(start_time=start_time, end_time=end_time, limit=limit)
        output = io.StringIO()
        writer = csv.writer(output)

        headers = ["feature_id", "timestamp_utc", "metric_id"] + list(FEATURE_COLUMNS)
        writer.writerow(headers)

        for f in features:
            row = [
                f.id,
                f.timestamp.isoformat() if f.timestamp else "",
                f.metric_id or "",
            ]
            for col in FEATURE_COLUMNS:
                row.append(f.features.get(col, ""))
            writer.writerow(row)

        return output.getvalue()

