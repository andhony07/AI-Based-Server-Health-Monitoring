"""Application logging configuration.

Sets up standard Python logging with structured formatting, supporting simultaneous
console output and rotating/persisted file output. Prevents duplicate handlers
on re-initialization and ensures target directories are safely created.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from app.core.config import Settings, get_settings

# Standard log format including timestamp, level, logger name, and message
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    settings: Optional[Settings] = None,
    log_file: Optional[Path] = None,
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Configure and initialize application logging.

    Ensures that log directories are safely created, both console (stdout)
    and file handlers are attached, and duplicate handlers are avoided when
    called multiple times.

    Args:
        settings: Application Settings instance. Defaults to current settings.
        log_file: Optional override for log output file path.
        log_level: Optional override for logging severity level.

    Returns:
        The configured 'app' logger instance.
    """
    cfg = settings or get_settings()
    level_name = (log_level or cfg.log_level).upper().strip()
    target_log_file = log_file or cfg.log_file

    numeric_level = getattr(logging, level_name, logging.INFO)

    # Safely create logs directory if it does not already exist
    target_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure the root logger so all child modules inherit settings
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to prevent duplicate logging on re-initialization
    if root_logger.handlers:
        for handler in list(root_logger.handlers):
            handler.close()
            root_logger.removeHandler(handler)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File Handler
    try:
        file_handler = logging.FileHandler(
            filename=str(target_log_file),
            mode="a",
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError as err:
        console_handler.handle(
            logging.LogRecord(
                name="app.core.logging",
                level=logging.ERROR,
                pathname=__file__,
                lineno=0,
                msg=f"Failed to initialize file logger at '{target_log_file}': {err}",
                args=(),
                exc_info=None,
            )
        )

    app_logger = logging.getLogger("app")
    app_logger.setLevel(numeric_level)
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance under the application namespace.

    Args:
        name: Name for the logger (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
