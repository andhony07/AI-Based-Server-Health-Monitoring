"""Unit tests for configuration management, directory handling, and logging setup."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest import mock

import pytest

from app.core.config import Settings, get_settings, load_config
from app.core.logging_config import setup_logging
from app.main import init_application, main


class TestConfiguration:
    """Test suite for application configuration management."""

    def test_default_configuration_loads_successfully(self) -> None:
        """Verify default configuration loads with correct types and sensible defaults."""
        settings = load_config()

        assert isinstance(settings, Settings)
        assert settings.app_name == "AI-Based Predictive System Health Monitoring"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.metric_collection_interval == 5.0
        assert isinstance(settings.metric_collection_interval, float)
        assert settings.max_processes == 10
        assert isinstance(settings.max_processes, int)
        assert settings.cpu_sample_interval is None
        assert settings.rolling_window_size == 12
        assert isinstance(settings.rolling_window_size, int)
        assert settings.max_history_size == 60
        assert isinstance(settings.max_history_size, int)
        assert settings.missing_value_strategy == "zero"
        assert settings.db_connection_timeout == 30.0
        assert isinstance(settings.db_connection_timeout, float)
        assert settings.db_auto_init is True
        assert settings.db_retention_days is None
        assert settings.ml_isolation_forest_n_estimators == 100
        assert settings.ml_isolation_forest_contamination == 0.05
        assert settings.ml_random_seed == 42
        assert settings.ml_min_training_samples == 20
        assert settings.ml_risk_threshold_low == 0.35
        assert settings.ml_risk_threshold_moderate == 0.55
        assert settings.ml_risk_threshold_high == 0.75
        assert settings.ml_risk_threshold_critical == 0.90

    def test_project_directories_represented_as_pathlib(self) -> None:
        """Verify all file and directory configurations use pathlib.Path objects."""
        settings = load_config()

        path_fields = [
            settings.base_dir,
            settings.data_dir,
            settings.raw_data_dir,
            settings.processed_data_dir,
            settings.models_dir,
            settings.logs_dir,
            settings.docs_dir,
            settings.log_file,
            settings.database_path,
        ]

        for path_field in path_fields:
            assert isinstance(
                path_field, Path
            ), f"Expected Path instance, got {type(path_field)}"

        # Validate directory hierarchy relationships
        assert settings.raw_data_dir.parent == settings.data_dir
        assert settings.processed_data_dir.parent == settings.data_dir
        assert settings.logs_dir.parent == settings.base_dir
        assert settings.models_dir.parent == settings.base_dir
        assert settings.data_dir.parent == settings.base_dir

    def test_settings_is_immutable(self) -> None:
        """Verify that Settings instances are frozen to prevent accidental global mutation."""
        settings = load_config()

        with pytest.raises(Exception):
            # Attempting to reassign a field on a frozen dataclass must raise
            settings.app_name = "New Name"  # type: ignore[misc]

    def test_environment_variable_overrides(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify configuration accurately reads and respects environment variables."""
        monkeypatch.setenv("APP_NAME", "Custom-Health-Monitor")
        monkeypatch.setenv("APP_VERSION", "2.0.0")
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("METRIC_COLLECTION_INTERVAL", "1.5")
        monkeypatch.setenv("MAX_PROCESSES", "25")
        monkeypatch.setenv("CPU_SAMPLE_INTERVAL", "0.2")
        monkeypatch.setenv("ROLLING_WINDOW_SIZE", "20")
        monkeypatch.setenv("MAX_HISTORY_SIZE", "100")
        monkeypatch.setenv("MISSING_VALUE_STRATEGY", "indicator")
        monkeypatch.setenv("DB_CONNECTION_TIMEOUT", "15.5")
        monkeypatch.setenv("DB_AUTO_INIT", "false")
        monkeypatch.setenv("DB_RETENTION_DAYS", "45")
        monkeypatch.setenv("ML_ISOLATION_FOREST_N_ESTIMATORS", "150")
        monkeypatch.setenv("ML_ISOLATION_FOREST_CONTAMINATION", "0.08")
        monkeypatch.setenv("ML_RANDOM_SEED", "99")
        monkeypatch.setenv("ML_MIN_TRAINING_SAMPLES", "50")
        monkeypatch.setenv("ML_RISK_THRESHOLD_LOW", "0.30")
        monkeypatch.setenv("ML_RISK_THRESHOLD_MODERATE", "0.50")
        monkeypatch.setenv("ML_RISK_THRESHOLD_HIGH", "0.70")
        monkeypatch.setenv("ML_RISK_THRESHOLD_CRITICAL", "0.85")

        settings = load_config()

        assert settings.app_name == "Custom-Health-Monitor"
        assert settings.app_version == "2.0.0"
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.metric_collection_interval == 1.5
        assert settings.max_processes == 25
        assert settings.cpu_sample_interval == 0.2
        assert settings.rolling_window_size == 20
        assert settings.max_history_size == 100
        assert settings.missing_value_strategy == "indicator"
        assert settings.db_connection_timeout == 15.5
        assert settings.db_auto_init is False
        assert settings.db_retention_days == 45
        assert settings.ml_isolation_forest_n_estimators == 150
        assert settings.ml_isolation_forest_contamination == 0.08
        assert settings.ml_random_seed == 99
        assert settings.ml_min_training_samples == 50
        assert settings.ml_risk_threshold_low == 0.30
        assert settings.ml_risk_threshold_moderate == 0.50
        assert settings.ml_risk_threshold_high == 0.70
        assert settings.ml_risk_threshold_critical == 0.85

    def test_invalid_log_level_raises_error(self) -> None:
        """Verify that invalid log level configuration raises a descriptive ValueError."""
        with pytest.raises(ValueError, match="Invalid log level 'INVALID_LEVEL'"):
            load_config(log_level="INVALID_LEVEL")

    def test_non_positive_metric_interval_raises_error(self) -> None:
        """Verify that zero or negative metric collection intervals raise a ValueError."""
        with pytest.raises(ValueError, match="Metric collection interval must be positive"):
            load_config(metric_collection_interval=0.0)

        with pytest.raises(ValueError, match="Metric collection interval must be positive"):
            load_config(metric_collection_interval=-2.5)

    def test_non_numeric_metric_interval_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify non-numeric metric intervals in env vars raise a ValueError."""
        monkeypatch.setenv("METRIC_COLLECTION_INTERVAL", "not-a-number")
        with pytest.raises(ValueError, match="Must be a numeric value"):
            load_config()

    def test_invalid_max_processes_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify invalid max_processes raises ValueError."""
        with pytest.raises(ValueError, match="max_processes must be positive"):
            load_config(max_processes=0)

        with pytest.raises(ValueError, match="max_processes must be positive"):
            load_config(max_processes=-5)

        monkeypatch.setenv("MAX_PROCESSES", "invalid-int")
        with pytest.raises(ValueError, match="Must be an integer"):
            load_config()

    def test_invalid_cpu_sample_interval_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify invalid cpu_sample_interval raises ValueError."""
        with pytest.raises(ValueError, match="cpu_sample_interval must be non-negative"):
            load_config(cpu_sample_interval=-0.5)

        monkeypatch.setenv("CPU_SAMPLE_INTERVAL", "invalid-float")
        with pytest.raises(ValueError, match="Must be a numeric value"):
            load_config()

    def test_invalid_rolling_window_size_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify invalid rolling_window_size raises ValueError."""
        with pytest.raises(ValueError, match="rolling_window_size must be positive"):
            load_config(rolling_window_size=0)

        with pytest.raises(ValueError, match="rolling_window_size must be positive"):
            load_config(rolling_window_size=-3)

        monkeypatch.setenv("ROLLING_WINDOW_SIZE", "not-an-int")
        with pytest.raises(ValueError, match="Must be an integer"):
            load_config()

    def test_invalid_max_history_size_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify max_history_size < rolling_window_size raises ValueError."""
        with pytest.raises(ValueError, match="must be >= rolling_window_size"):
            load_config(rolling_window_size=20, max_history_size=10)

        monkeypatch.setenv("MAX_HISTORY_SIZE", "not-an-int")
        with pytest.raises(ValueError, match="Must be an integer"):
            load_config()

    def test_invalid_missing_value_strategy_raises_error(self) -> None:
        """Verify invalid missing_value_strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid missing_value_strategy"):
            load_config(missing_value_strategy="unsupported_strategy")

    def test_invalid_db_connection_timeout_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify invalid db_connection_timeout raises ValueError."""
        with pytest.raises(ValueError, match="db_connection_timeout must be positive"):
            load_config(db_connection_timeout=0.0)

        with pytest.raises(ValueError, match="db_connection_timeout must be positive"):
            load_config(db_connection_timeout=-5.0)

        monkeypatch.setenv("DB_CONNECTION_TIMEOUT", "invalid-float")
        with pytest.raises(ValueError, match="Must be a numeric value"):
            load_config()

    def test_invalid_db_retention_days_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify invalid db_retention_days raises ValueError."""
        with pytest.raises(ValueError, match="db_retention_days must be a positive integer"):
            load_config(db_retention_days=0)

        with pytest.raises(ValueError, match="db_retention_days must be a positive integer"):
            load_config(db_retention_days=-10)

        monkeypatch.setenv("DB_RETENTION_DAYS", "not-an-integer")
        with pytest.raises(ValueError, match="Must be an integer"):
            load_config()

    def test_invalid_ml_settings_raise_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify invalid ML settings raise informative ValueErrors."""
        with pytest.raises(ValueError, match="ml_isolation_forest_n_estimators must be positive"):
            load_config(ml_isolation_forest_n_estimators=0)

        with pytest.raises(ValueError, match="ml_isolation_forest_contamination must be in"):
            load_config(ml_isolation_forest_contamination=0.0)

        with pytest.raises(ValueError, match="ml_isolation_forest_contamination must be in"):
            load_config(ml_isolation_forest_contamination=0.7)

        with pytest.raises(ValueError, match="ml_min_training_samples must be at least 2"):
            load_config(ml_min_training_samples=1)

        with pytest.raises(ValueError, match="Risk thresholds must satisfy"):
            load_config(ml_risk_threshold_low=0.6, ml_risk_threshold_moderate=0.4)

        monkeypatch.setenv("ML_ISOLATION_FOREST_N_ESTIMATORS", "invalid-int")
        with pytest.raises(ValueError, match="Must be an integer"):
            load_config()

        monkeypatch.setenv("ML_ISOLATION_FOREST_N_ESTIMATORS", "100")
        monkeypatch.setenv("ML_ISOLATION_FOREST_CONTAMINATION", "invalid-float")
        with pytest.raises(ValueError, match="Must be a numeric value"):
            load_config()

    def test_ensure_directories_creates_all_folders(self, tmp_path: Path) -> None:
        """Verify ensure_directories safely creates all application folder paths."""
        custom_base = tmp_path / "custom_project"
        custom_db_dir = tmp_path / "custom_db_dir" / "nested" / "system.db"
        settings = load_config(base_dir=custom_base, database_path=str(custom_db_dir))

        # Before calling ensure_directories, directories should not exist
        assert not settings.data_dir.exists()
        assert not settings.raw_data_dir.exists()
        assert not settings.processed_data_dir.exists()
        assert not settings.models_dir.exists()
        assert not settings.logs_dir.exists()
        assert not settings.database_path.parent.exists()

        settings.ensure_directories()

        assert settings.data_dir.is_dir()
        assert settings.raw_data_dir.is_dir()
        assert settings.processed_data_dir.is_dir()
        assert settings.models_dir.is_dir()
        assert settings.logs_dir.is_dir()
        assert settings.docs_dir.is_dir()
        assert settings.database_path.parent.is_dir()

        # Calling a second time should not raise an error (exist_ok=True)
        settings.ensure_directories()


class TestLoggingSubsystem:
    """Test suite for logging configuration and handler lifecycle."""

    def test_logging_initialization_prevents_duplicate_handlers(
        self, tmp_path: Path
    ) -> None:
        """Verify multiple calls to setup_logging do not accumulate duplicate handlers."""
        log_file = tmp_path / "test_logs" / "test.log"
        settings = load_config(log_file=str(log_file))

        # First initialization
        logger1 = setup_logging(settings=settings, log_file=log_file)
        root_logger = logging.getLogger()

        # Should have exactly 1 StreamHandler (stdout) and 1 FileHandler
        initial_handler_count = len(root_logger.handlers)
        stream_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        ]
        file_handlers = [
            h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
        ]

        assert len(stream_handlers) == 1
        assert len(file_handlers) == 1
        assert initial_handler_count == 2

        # Second initialization (simulating multiple imports or re-configs)
        logger2 = setup_logging(settings=settings, log_file=log_file)
        reinit_handler_count = len(root_logger.handlers)

        assert reinit_handler_count == 2, (
            f"Handlers accumulated on re-initialization: {reinit_handler_count} handlers found."
        )

        # Third initialization
        setup_logging(settings=settings, log_file=log_file)
        assert len(root_logger.handlers) == 2

    def test_logging_writes_to_file(self, tmp_path: Path) -> None:
        """Verify that log records are properly written to disk with expected formatting."""
        log_file = tmp_path / "test_run.log"
        settings = load_config(log_file=str(log_file), log_level="DEBUG")

        logger = setup_logging(settings=settings, log_file=log_file, log_level="DEBUG")
        test_message = "Diagnostic health check probe message"
        logger.info(test_message)

        # Flush all handlers to disk
        for handler in logging.getLogger().handlers:
            handler.flush()

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert test_message in content
        assert "[INFO]" in content
        assert "[app]" in content


class TestApplicationLifecycle:
    """Test suite for entry point startup and verification."""

    def test_init_application_returns_valid_instances(self) -> None:
        """Verify init_application produces valid Settings and Logger instances."""
        settings, logger = init_application()

        assert isinstance(settings, Settings)
        assert isinstance(logger, logging.Logger)
        assert settings.logs_dir.exists()

    def test_main_startup_returns_zero_exit_code(self) -> None:
        """Verify main() function executes without error and returns exit code 0."""
        exit_code = main()
        assert exit_code == 0

    def test_main_graceful_error_handling(self) -> None:
        """Verify main() captures exceptions gracefully and returns non-zero exit code."""
        with mock.patch("app.main.init_application", side_effect=RuntimeError("Simulated failure")):
            exit_code = main()
            assert exit_code == 1
