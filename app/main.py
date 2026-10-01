"""Application entry point and initialization lifecycle.

Coordinates configuration loading, directory initialization, logging setup,
and real-time system telemetry metric collection loop.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from typing import Optional, Tuple

from app.collectors.system_collector import SystemCollector
from app.core.config import Settings, load_config
from app.core.logging_config import setup_logging
from app.database.service import PersistenceService
from app.ml.prediction_service import PredictionService
from app.models.metrics import SystemMetrics
from app.preprocessing.pipeline import PreprocessingPipeline


def init_application() -> Tuple[Settings, logging.Logger]:
    """Initialize application settings, directory layout, and logging subsystem.

    Returns:
        A tuple of (Settings, logging.Logger) ready for application use.

    Raises:
        Exception: If configuration validation or directory creation fails.
    """
    # 1. Load and validate configuration
    settings = load_config()

    # 2. Ensure project directories are established
    settings.ensure_directories()

    # 3. Initialize structured logging
    logger = setup_logging(settings)

    return settings, logger


def format_metrics_summary(metrics: SystemMetrics) -> str:
    """Format a concise, human-readable single-line summary of system metrics.

    Args:
        metrics: The harvested SystemMetrics snapshot.

    Returns:
        Formatted summary string.
    """
    cpu_str = (
        f"CPU: {metrics.cpu.utilization_percent:5.1f}% ({metrics.cpu.logical_cores} cores)"
        if metrics.cpu
        else "CPU: N/A"
    )
    mem_str = (
        f"RAM: {metrics.memory.utilization_percent:5.1f}% ({metrics.memory.used_mb:,.0f}/{metrics.memory.total_mb:,.0f} MB)"
        if metrics.memory
        else "RAM: N/A"
    )
    disk_str = (
        f"Disk: {metrics.disk.utilization_percent:5.1f}% ({metrics.disk.used_bytes / (1024**3):.1f} GB used)"
        if metrics.disk
        else "Disk: N/A"
    )
    net_str = (
        f"Net: TX {metrics.network.upload_kbps:6.1f} KB/s  RX {metrics.network.download_kbps:6.1f} KB/s"
        if metrics.network
        else "Net: N/A"
    )
    proc_count = len(metrics.processes)
    proc_str = f"Top Processes: {proc_count}"

    summary = f"{cpu_str} | {mem_str} | {disk_str} | {net_str} | {proc_str}"
    if metrics.errors:
        summary += f" | Errors: {len(metrics.errors)}"
    return summary


def main(
    single_shot: Optional[bool] = None,
    max_iterations: Optional[int] = None,
) -> int:
    """Execute application startup sequence and run the telemetry collection engine.

    Args:
        single_shot: If True, execute a single collection pass and return immediately.
        max_iterations: Optional limit on the number of periodic collection cycles.

    Returns:
        Exit code: 0 on successful execution or clean shutdown, non-zero on fatal failure.
    """
    try:
        settings, logger = init_application()

        logger.info("==================================================")
        logger.info("Starting %s (v%s)", settings.app_name, settings.app_version)
        logger.info("Environment: %s | Log Level: %s", settings.environment, settings.log_level)
        logger.info("Base Directory: %s", settings.base_dir)
        logger.info("Data Directory: %s", settings.data_dir)
        logger.info("Logs Directory: %s", settings.logs_dir)
        logger.info("Models Directory: %s", settings.models_dir)
        logger.info(
            "Configured Metrics Interval: %.1fs | Max Monitored Processes: %d",
            settings.metric_collection_interval,
            settings.max_processes,
        )
        logger.info("Initializing Telemetry Collection, Preprocessing Pipeline, and Persistence Service...")

        collector = SystemCollector(settings=settings)
        pipeline = PreprocessingPipeline(settings=settings)
        db_service = PersistenceService(settings=settings)
        pred_service = PredictionService(settings=settings)
        logger.info("All telemetry collectors, preprocessing pipeline, persistence, and prediction services initialized.")
        logger.info("==================================================")

        # Check for training mode CLI invocation
        if "--train" in sys.argv:
            from app.ml.training import ModelTrainer, InsufficientDataError
            logger.info("Training mode requested via CLI flag.")
            trainer = ModelTrainer(settings=settings)
            try:
                _, metadata = trainer.train_isolation_forest()
                logger.info(
                    "Model trained successfully: %s (v%s) with %d samples. Baseline anomaly rate: %.2f%%",
                    metadata.model_name,
                    metadata.version,
                    metadata.training_samples_count,
                    metadata.metrics.get("anomaly_rate", 0.0) * 100,
                )
                db_service.close()
                return 0
            except InsufficientDataError as err:
                logger.warning("Model training deferred: %s", err)
                db_service.close()
                return 1
            except Exception as train_exc:
                logger.error("Model training failed: %s", train_exc, exc_info=True)
                db_service.close()
                return 1

        # Check for dashboard mode CLI invocation
        if "--dashboard" in sys.argv or "-d" in sys.argv:
            import subprocess
            logger.info("Launching Streamlit Web Dashboard on port %d...", settings.dashboard_port)
            dash_path = settings.base_dir / "app" / "dashboard" / "app.py"
            cmd = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(dash_path),
                "--server.port",
                str(settings.dashboard_port),
            ]
            db_service.close()
            return subprocess.call(cmd)

        # Detect single-shot or test execution mode
        is_test_env = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
        cli_single_shot = "--single-shot" in sys.argv or "--oneshot" in sys.argv
        env_single_shot = os.getenv("MONITOR_SINGLE_SHOT", "").lower() in ("1", "true", "yes")

        run_single = (
            single_shot
            if single_shot is not None
            else (cli_single_shot or env_single_shot or is_test_env)
        )

        if run_single:
            # Single-pass verification mode
            metrics = collector.collect()
            processed = pipeline.process(metrics)
            summary = format_metrics_summary(metrics)
            logger.info("Collected telemetry snapshot: %s", summary)
            logger.info(
                "Extracted %d numerical features (validation_valid=%s, issues=%d)",
                len(processed.feature_vector.features),
                processed.validation_result.is_valid,
                len(processed.validation_result.issues),
            )
            # Atomically persist single-shot sample
            persist_res = db_service.persist_sample(metrics, processed)
            if persist_res.success:
                logger.info(
                    "Persisted sample to database (metric_id=%s, feature_id=%s, validation_id=%s)",
                    persist_res.metric_id,
                    persist_res.feature_id,
                    persist_res.validation_id,
                )
            else:
                logger.warning("Database persistence failed: %s", persist_res.error_message)

            # Evaluate system health and anomaly risk via ML PredictionService
            try:
                prediction = pred_service.predict(processed)
                health_str = f"{prediction.health_score:.1f}/100" if prediction.health_score is not None else "N/A"
                logger.info(
                    "[PREDICTION] Risk: %s | Anomaly: %s (score=%.4f) | Health: %s | Model: %s",
                    prediction.risk_category.value,
                    prediction.is_anomaly,
                    prediction.anomaly_score,
                    health_str,
                    prediction.model_name,
                )
                if prediction.warnings:
                    for warn in prediction.warnings:
                        logger.debug("[PREDICTION WARNING] %s", warn)
            except Exception as ml_exc:
                logger.warning("Prediction inference encountered an error: %s", ml_exc)

            if metrics.errors:
                for err in metrics.errors:
                    logger.warning("Telemetry warning: %s", err)
            db_service.close()
            return 0

        # Periodic monitoring mode with signal-aware graceful shutdown
        stop_event = threading.Event()

        def _handle_exit_signal(signum: int, _frame: object) -> None:
            sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
            logger.info("Received signal %s; requesting clean shutdown...", sig_name)
            stop_event.set()

        try:
            signal.signal(signal.SIGINT, _handle_exit_signal)
            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, _handle_exit_signal)
        except (ValueError, AttributeError):  # pragma: no cover
            pass

        def on_metric_sample(sample: SystemMetrics) -> None:
            processed = pipeline.process(sample)
            summary = format_metrics_summary(sample)
            logger.info(
                "[METRICS] %s | Features: %d",
                summary,
                len(processed.feature_vector.features),
            )
            # Atomically persist sample to database
            persist_res = db_service.persist_sample(sample, processed)
            if persist_res.success:
                logger.debug(
                    "Persisted sample to DB (metric_id=%s, feature_id=%s)",
                    persist_res.metric_id,
                    persist_res.feature_id,
                )
            else:
                logger.warning(
                    "Database persistence failed for sample: %s",
                    persist_res.error_message,
                )

            # Evaluate system health and anomaly risk via ML PredictionService
            try:
                prediction = pred_service.predict(processed)
                health_str = f"{prediction.health_score:.1f}/100" if prediction.health_score is not None else "N/A"
                logger.info(
                    "[PREDICTION] Risk: %s | Anomaly: %s (score=%.4f) | Health: %s",
                    prediction.risk_category.value,
                    prediction.is_anomaly,
                    prediction.anomaly_score,
                    health_str,
                )
                if prediction.warnings:
                    for warn in prediction.warnings:
                        logger.debug("[PREDICTION WARNING] %s", warn)
            except Exception as ml_exc:
                logger.warning("Prediction inference encountered an error: %s", ml_exc)

            if sample.errors:
                for err in sample.errors:
                    logger.warning("[COLLECTOR ERROR] %s", err)
            if processed.validation_result.issues:
                for issue in processed.validation_result.issues:
                    logger.debug("[VALIDATION ISSUE] %s: %s", issue.domain, issue.message)

        collector.run_collection_loop(
            interval=settings.metric_collection_interval,
            callback=on_metric_sample,
            stop_event=stop_event,
            max_iterations=max_iterations,
        )

        db_service.close()
        logger.info("System health monitoring engine shut down cleanly.")
        return 0

    except Exception as exc:
        sys.stderr.write(f"FATAL: Application execution failed: {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
