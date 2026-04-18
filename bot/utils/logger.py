"""
Logging setup using loguru.

Provides a pre-configured logger instance and a helper to add file/rotation sinks.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "50 MB",
    retention: str = "30 days",
    compression: str = "gz",
) -> None:
    """
    Configure loguru with console and optional file logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Path to log file. If None, only console logging is used.
        rotation: When to rotate the log file (e.g. "50 MB", "00:00").
        retention: How long to keep old log files (e.g. "30 days").
        compression: Compression for rotated logs (e.g. "gz", "zip").
    """
    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # Optional file handler with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            level=log_level,
            format=(
                "{time:YYYY-MM-DD HH:mm:ss} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,  # Thread-safe async writing
        )

    logger.info(f"Logger initialized — level={log_level}, file={log_file or 'none'}")


# Convenience export
__all__ = ["logger", "setup_logger"]
