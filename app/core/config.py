"""Centralized application configuration management.

Provides a robust, cross-platform configuration model using pathlib,
dataclasses, and environment variable support via python-dotenv.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from dotenv import load_dotenv

# Recognized logging levels for validation
VALID_LOG_LEVELS: Final[set[str]] = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

# Resolve project base directory relative to this file:
# app/core/config.py -> core -> app -> project_root
DEFAULT_BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Settings:
    """Immutable application settings container.

    Attributes:
        app_name: Name of the application.
        app_version: Application version identifier.
        environment: Deployment environment (development, testing, production).
        log_level: Configured log severity level.
        metric_collection_interval: Sampling interval in seconds for metrics collection.
        base_dir: Root directory of the project.
        data_dir: Base directory for storing application data.
        raw_data_dir: Directory for storing raw telemetry records.
        processed_data_dir: Directory for storing cleaned/transformed features.
        models_dir: Directory for persisting trained machine learning models.
        logs_dir: Directory for storing application log files.
        docs_dir: Directory containing project architecture and documentation.
        log_file: Default destination file for file-based logging.
        database_path: Filepath for the SQLite historical metrics database.
        max_processes: Maximum number of top processes to monitor (default 10).
        cpu_sample_interval: Optional blocking sample interval in seconds for CPU utilization.
        rolling_window_size: Number of samples in the sliding statistics window (default 12).
        max_history_size: Maximum bounded samples retained in rolling buffer (default 60).
        missing_value_strategy: Strategy for missing metric imputation ('zero', 'indicator', 'last_valid').
        db_connection_timeout: SQLite connection timeout in seconds (default 30.0).
        db_auto_init: Whether to automatically initialize database schema on startup (default True).
        db_retention_days: Optional retention threshold in days for purging old telemetry.
        ml_isolation_forest_n_estimators: Number of trees in Isolation Forest (default 100).
        ml_isolation_forest_contamination: Expected proportion of outliers/anomalies (default 0.05).
        ml_random_seed: Random seed for deterministic ML operations (default 42).
        ml_min_training_samples: Minimum historical samples required to train models (default 20).
        ml_risk_threshold_low: Normalized anomaly threshold for Low risk category (default 0.35).
        ml_risk_threshold_moderate: Normalized anomaly threshold for Moderate risk category (default 0.55).
        ml_risk_threshold_high: Normalized anomaly threshold for High risk category (default 0.75).
        ml_risk_threshold_critical: Normalized anomaly threshold for Critical risk category (default 0.90).
        dashboard_refresh_interval: Interval in seconds for dashboard auto-refresh (default 5).
        dashboard_historical_limit: Maximum historical records loaded by default (default 500).
        dashboard_port: Port number for Streamlit web dashboard (default 8501).
    """

    app_name: str
    app_version: str
    environment: str
    log_level: str
    metric_collection_interval: float
    base_dir: Path
    data_dir: Path
    raw_data_dir: Path
    processed_data_dir: Path
    models_dir: Path
    logs_dir: Path
    docs_dir: Path
    log_file: Path
    database_path: Path
    max_processes: int = 10
    cpu_sample_interval: Optional[float] = None
    rolling_window_size: int = 12
    max_history_size: int = 60
    missing_value_strategy: str = "zero"
    db_connection_timeout: float = 30.0
    db_auto_init: bool = True
    db_retention_days: Optional[int] = None
    ml_isolation_forest_n_estimators: int = 100
    ml_isolation_forest_contamination: float = 0.05
    ml_random_seed: int = 42
    ml_min_training_samples: int = 20
    ml_risk_threshold_low: float = 0.35
    ml_risk_threshold_moderate: float = 0.55
    ml_risk_threshold_high: float = 0.75
    ml_risk_threshold_critical: float = 0.90
    dashboard_refresh_interval: int = 5
    dashboard_historical_limit: int = 500
    dashboard_port: int = 8501

    def __post_init__(self) -> None:
        """Validate configuration settings values."""
        normalized_log_level = self.log_level.upper().strip()
        if normalized_log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level '{self.log_level}'. Must be one of: "
                f"{', '.join(sorted(VALID_LOG_LEVELS))}"
            )

        if self.metric_collection_interval <= 0:
            raise ValueError(
                f"Metric collection interval must be positive, got: "
                f"{self.metric_collection_interval}"
            )

        if self.max_processes <= 0:
            raise ValueError(
                f"max_processes must be positive, got: {self.max_processes}"
            )

        if self.cpu_sample_interval is not None and self.cpu_sample_interval < 0:
            raise ValueError(
                f"cpu_sample_interval must be non-negative, got: {self.cpu_sample_interval}"
            )

        if self.rolling_window_size <= 0:
            raise ValueError(
                f"rolling_window_size must be positive, got: {self.rolling_window_size}"
            )

        if self.max_history_size < self.rolling_window_size:
            raise ValueError(
                f"max_history_size ({self.max_history_size}) must be >= "
                f"rolling_window_size ({self.rolling_window_size})"
            )

        valid_missing_strategies = {"zero", "indicator", "last_valid"}
        if self.missing_value_strategy.lower().strip() not in valid_missing_strategies:
            raise ValueError(
                f"Invalid missing_value_strategy '{self.missing_value_strategy}'. Must be one of: "
                f"{', '.join(sorted(valid_missing_strategies))}"
            )

        if self.db_connection_timeout <= 0:
            raise ValueError(
                f"db_connection_timeout must be positive, got: {self.db_connection_timeout}"
            )

        if self.db_retention_days is not None and self.db_retention_days <= 0:
            raise ValueError(
                f"db_retention_days must be a positive integer, got: {self.db_retention_days}"
            )

        if self.ml_isolation_forest_n_estimators <= 0:
            raise ValueError(
                f"ml_isolation_forest_n_estimators must be positive, got: {self.ml_isolation_forest_n_estimators}"
            )

        if not (0.0 < self.ml_isolation_forest_contamination <= 0.5):
            raise ValueError(
                f"ml_isolation_forest_contamination must be in (0.0, 0.5], got: {self.ml_isolation_forest_contamination}"
            )

        if self.ml_min_training_samples < 2:
            raise ValueError(
                f"ml_min_training_samples must be at least 2, got: {self.ml_min_training_samples}"
            )

        if not (
            0.0
            <= self.ml_risk_threshold_low
            < self.ml_risk_threshold_moderate
            < self.ml_risk_threshold_high
            < self.ml_risk_threshold_critical
            <= 1.0
        ):
            raise ValueError(
                "Risk thresholds must satisfy 0.0 <= low < moderate < high < critical <= 1.0"
            )

        if self.dashboard_refresh_interval <= 0:
            raise ValueError(
                f"dashboard_refresh_interval must be positive, got: {self.dashboard_refresh_interval}"
            )

        if self.dashboard_historical_limit <= 0:
            raise ValueError(
                f"dashboard_historical_limit must be positive, got: {self.dashboard_historical_limit}"
            )

        if not (1024 <= self.dashboard_port <= 65535):
            raise ValueError(
                f"dashboard_port must be in range [1024, 65535], got: {self.dashboard_port}"
            )

    def ensure_directories(self) -> None:
        """Ensure all standard application directories exist on the filesystem."""
        directories = [
            self.data_dir,
            self.raw_data_dir,
            self.processed_data_dir,
            self.models_dir,
            self.logs_dir,
            self.docs_dir,
            self.database_path.parent,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


def load_config(
    env_file: Optional[Path] = None,
    base_dir: Optional[Path] = None,
    **overrides: object,
) -> Settings:
    """Load configuration from environment variables, optional .env file, and defaults.

    Args:
        env_file: Optional path to a specific .env file. If not provided,
            checks for .env in the base directory.
        base_dir: Optional base directory override. Defaults to DEFAULT_BASE_DIR.
        **overrides: Explicit key-value overrides for testing or runtime injection.

    Returns:
        A validated, immutable Settings instance.
    """
    resolved_base_dir = (
        Path(base_dir).resolve() if base_dir is not None else DEFAULT_BASE_DIR
    )

    # Load environment variables from .env if available
    target_env = env_file if env_file is not None else resolved_base_dir / ".env"
    if target_env.exists():
        load_dotenv(dotenv_path=target_env, override=False)

    app_name = str(
        overrides.get(
            "app_name",
            os.getenv("APP_NAME", "AI-Based Predictive System Health Monitoring"),
        )
    )
    app_version = str(overrides.get("app_version", os.getenv("APP_VERSION", "0.1.0")))
    environment = str(
        overrides.get("environment", os.getenv("APP_ENV", "development"))
    )

    raw_log_level = str(
        overrides.get("log_level", os.getenv("LOG_LEVEL", "INFO"))
    ).upper().strip()

    # Metric collection interval in seconds
    raw_interval = overrides.get(
        "metric_collection_interval",
        os.getenv("METRIC_COLLECTION_INTERVAL", "5.0"),
    )
    try:
        metric_collection_interval = float(raw_interval)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid METRIC_COLLECTION_INTERVAL: '{raw_interval}'. Must be a numeric value."
        ) from err

    # Resolve directories relative to project base_dir
    data_dirname = str(overrides.get("data_dir", os.getenv("DATA_DIR", "data")))
    models_dirname = str(
        overrides.get("models_dir", os.getenv("MODELS_DIR", "models"))
    )
    logs_dirname = str(overrides.get("logs_dir", os.getenv("LOGS_DIR", "logs")))

    data_dir = (
        Path(data_dirname)
        if Path(data_dirname).is_absolute()
        else (resolved_base_dir / data_dirname)
    )
    raw_data_dir = data_dir / "raw"
    processed_data_dir = data_dir / "processed"

    models_dir = (
        Path(models_dirname)
        if Path(models_dirname).is_absolute()
        else (resolved_base_dir / models_dirname)
    )
    logs_dir = (
        Path(logs_dirname)
        if Path(logs_dirname).is_absolute()
        else (resolved_base_dir / logs_dirname)
    )
    docs_dir = resolved_base_dir / "docs"

    log_filename = str(
        overrides.get("log_file", os.getenv("LOG_FILE", "system_monitor.log"))
    )
    log_file = (
        Path(log_filename)
        if Path(log_filename).is_absolute()
        else (logs_dir / log_filename)
    )

    db_filename = str(
        overrides.get("database_path", os.getenv("DB_PATH", "system_metrics.db"))
    )
    database_path = (
        Path(db_filename)
        if Path(db_filename).is_absolute()
        else (data_dir / db_filename)
    )

    # Process monitoring limits (Phase 2)
    raw_max_proc = overrides.get("max_processes", os.getenv("MAX_PROCESSES", "10"))
    try:
        max_processes = int(raw_max_proc)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid MAX_PROCESSES: '{raw_max_proc}'. Must be an integer."
        ) from err

    # Optional blocking CPU sampling interval (Phase 2)
    raw_cpu_sample = overrides.get(
        "cpu_sample_interval", os.getenv("CPU_SAMPLE_INTERVAL")
    )
    cpu_sample_interval: Optional[float] = None
    if raw_cpu_sample is not None and str(raw_cpu_sample).strip() != "":
        try:
            cpu_sample_interval = float(raw_cpu_sample)  # type: ignore[arg-type]
        except (TypeError, ValueError) as err:
            raise ValueError(
                f"Invalid CPU_SAMPLE_INTERVAL: '{raw_cpu_sample}'. Must be a numeric value."
            ) from err

    # Preprocessing & Feature Engineering Settings (Phase 3)
    raw_window = overrides.get(
        "rolling_window_size", os.getenv("ROLLING_WINDOW_SIZE", "12")
    )
    try:
        rolling_window_size = int(raw_window)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ROLLING_WINDOW_SIZE: '{raw_window}'. Must be an integer."
        ) from err

    raw_history = overrides.get(
        "max_history_size", os.getenv("MAX_HISTORY_SIZE", "60")
    )
    try:
        max_history_size = int(raw_history)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid MAX_HISTORY_SIZE: '{raw_history}'. Must be an integer."
        ) from err

    missing_value_strategy = str(
        overrides.get(
            "missing_value_strategy",
            os.getenv("MISSING_VALUE_STRATEGY", "zero"),
        )
    ).lower().strip()

    # Database connection and persistence settings (Phase 4)
    raw_db_timeout = overrides.get(
        "db_connection_timeout", os.getenv("DB_CONNECTION_TIMEOUT", "30.0")
    )
    try:
        db_connection_timeout = float(raw_db_timeout)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid DB_CONNECTION_TIMEOUT: '{raw_db_timeout}'. Must be a numeric value."
        ) from err

    raw_db_auto_init = overrides.get(
        "db_auto_init", os.getenv("DB_AUTO_INIT", "true")
    )
    if isinstance(raw_db_auto_init, bool):
        db_auto_init = raw_db_auto_init
    else:
        db_auto_init = str(raw_db_auto_init).lower().strip() in (
            "1",
            "true",
            "yes",
            "on",
        )

    raw_retention = overrides.get(
        "db_retention_days", os.getenv("DB_RETENTION_DAYS")
    )
    db_retention_days: Optional[int] = None
    if raw_retention is not None and str(raw_retention).strip() != "":
        try:
            db_retention_days = int(raw_retention)  # type: ignore[arg-type]
        except (TypeError, ValueError) as err:
            raise ValueError(
                f"Invalid DB_RETENTION_DAYS: '{raw_retention}'. Must be an integer."
            ) from err

    # Machine Learning & Risk Analysis settings (Phase 5)
    raw_n_estimators = overrides.get(
        "ml_isolation_forest_n_estimators",
        os.getenv("ML_ISOLATION_FOREST_N_ESTIMATORS", os.getenv("ML_N_ESTIMATORS", "100")),
    )
    try:
        ml_isolation_forest_n_estimators = int(raw_n_estimators)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_ISOLATION_FOREST_N_ESTIMATORS: '{raw_n_estimators}'. Must be an integer."
        ) from err

    raw_contamination = overrides.get(
        "ml_isolation_forest_contamination",
        os.getenv("ML_ISOLATION_FOREST_CONTAMINATION", os.getenv("ML_CONTAMINATION", "0.05")),
    )
    try:
        ml_isolation_forest_contamination = float(raw_contamination)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_ISOLATION_FOREST_CONTAMINATION: '{raw_contamination}'. Must be a numeric value."
        ) from err

    raw_random_seed = overrides.get(
        "ml_random_seed", os.getenv("ML_RANDOM_SEED", "42")
    )
    try:
        ml_random_seed = int(raw_random_seed)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_RANDOM_SEED: '{raw_random_seed}'. Must be an integer."
        ) from err

    raw_min_samples = overrides.get(
        "ml_min_training_samples", os.getenv("ML_MIN_TRAINING_SAMPLES", "20")
    )
    try:
        ml_min_training_samples = int(raw_min_samples)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_MIN_TRAINING_SAMPLES: '{raw_min_samples}'. Must be an integer."
        ) from err

    raw_thresh_low = overrides.get(
        "ml_risk_threshold_low", os.getenv("ML_RISK_THRESHOLD_LOW", "0.35")
    )
    try:
        ml_risk_threshold_low = float(raw_thresh_low)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_RISK_THRESHOLD_LOW: '{raw_thresh_low}'. Must be a numeric value."
        ) from err

    raw_thresh_mod = overrides.get(
        "ml_risk_threshold_moderate",
        os.getenv("ML_RISK_THRESHOLD_MODERATE", "0.55"),
    )
    try:
        ml_risk_threshold_moderate = float(raw_thresh_mod)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_RISK_THRESHOLD_MODERATE: '{raw_thresh_mod}'. Must be a numeric value."
        ) from err

    raw_thresh_high = overrides.get(
        "ml_risk_threshold_high", os.getenv("ML_RISK_THRESHOLD_HIGH", "0.75")
    )
    try:
        ml_risk_threshold_high = float(raw_thresh_high)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_RISK_THRESHOLD_HIGH: '{raw_thresh_high}'. Must be a numeric value."
        ) from err

    raw_thresh_crit = overrides.get(
        "ml_risk_threshold_critical",
        os.getenv("ML_RISK_THRESHOLD_CRITICAL", "0.90"),
    )
    try:
        ml_risk_threshold_critical = float(raw_thresh_crit)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid ML_RISK_THRESHOLD_CRITICAL: '{raw_thresh_crit}'. Must be a numeric value."
        ) from err

    # Dashboard settings (Phase 6)
    raw_dash_refresh = overrides.get(
        "dashboard_refresh_interval",
        os.getenv("DASHBOARD_REFRESH_INTERVAL", "5"),
    )
    try:
        dashboard_refresh_interval = int(raw_dash_refresh)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid DASHBOARD_REFRESH_INTERVAL: '{raw_dash_refresh}'. Must be an integer."
        ) from err

    raw_dash_hist = overrides.get(
        "dashboard_historical_limit",
        os.getenv("DASHBOARD_HISTORICAL_LIMIT", "500"),
    )
    try:
        dashboard_historical_limit = int(raw_dash_hist)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid DASHBOARD_HISTORICAL_LIMIT: '{raw_dash_hist}'. Must be an integer."
        ) from err

    raw_dash_port = overrides.get(
        "dashboard_port",
        os.getenv("DASHBOARD_PORT", "8501"),
    )
    try:
        dashboard_port = int(raw_dash_port)  # type: ignore[arg-type]
    except (TypeError, ValueError) as err:
        raise ValueError(
            f"Invalid DASHBOARD_PORT: '{raw_dash_port}'. Must be an integer."
        ) from err

    return Settings(
        app_name=app_name,
        app_version=app_version,
        environment=environment,
        log_level=raw_log_level,
        metric_collection_interval=metric_collection_interval,
        base_dir=resolved_base_dir,
        data_dir=data_dir,
        raw_data_dir=raw_data_dir,
        processed_data_dir=processed_data_dir,
        models_dir=models_dir,
        logs_dir=logs_dir,
        docs_dir=docs_dir,
        log_file=log_file,
        database_path=database_path,
        max_processes=max_processes,
        cpu_sample_interval=cpu_sample_interval,
        rolling_window_size=rolling_window_size,
        max_history_size=max_history_size,
        missing_value_strategy=missing_value_strategy,
        db_connection_timeout=db_connection_timeout,
        db_auto_init=db_auto_init,
        db_retention_days=db_retention_days,
        ml_isolation_forest_n_estimators=ml_isolation_forest_n_estimators,
        ml_isolation_forest_contamination=ml_isolation_forest_contamination,
        ml_random_seed=ml_random_seed,
        ml_min_training_samples=ml_min_training_samples,
        ml_risk_threshold_low=ml_risk_threshold_low,
        ml_risk_threshold_moderate=ml_risk_threshold_moderate,
        ml_risk_threshold_high=ml_risk_threshold_high,
        ml_risk_threshold_critical=ml_risk_threshold_critical,
        dashboard_refresh_interval=dashboard_refresh_interval,
        dashboard_historical_limit=dashboard_historical_limit,
        dashboard_port=dashboard_port,
    )


def get_settings() -> Settings:
    """Convenience getter returning a fresh Settings instance based on current environment.

    Returns:
        Loaded Settings instance.
    """
    return load_config()
