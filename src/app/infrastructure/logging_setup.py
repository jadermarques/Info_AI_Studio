"""Central logging configuration for the application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import get_settings

FULL_LOG_LEVEL = 15
logging.addLevelName(FULL_LOG_LEVEL, "FULL")


def _log_full(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(FULL_LOG_LEVEL):
        self._log(FULL_LOG_LEVEL, message, args, **kwargs)


if not hasattr(logging.Logger, "full"):
    logging.Logger.full = _log_full  # type: ignore[attr-defined]


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """Configure root logging with console and optional file handler."""

    logger = logging.getLogger()
    if not logger.handlers:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
        console = logging.StreamHandler()
        console.setLevel(numeric_level)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console.setFormatter(formatter)
        logger.addHandler(console)
    if log_file is not None:
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_file):
                break
        else:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            )
            logger.addHandler(file_handler)
    return logger


def get_log_file_path(filename: str) -> Path:
    """Return a path inside the configured log directory."""

    settings = get_settings()
    return settings.log_dir / filename
