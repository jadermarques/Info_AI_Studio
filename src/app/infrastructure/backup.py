"""Backup utilities for the SQLite database."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from app.config import get_settings

LOGGER = logging.getLogger(__name__)


def create_backup() -> Path:
    """Create a timestamped copy of the database file."""

    settings = get_settings()
    db_path = settings.db_path
    if not db_path.exists():
        msg = (
            "Banco de dados não encontrado. Inicialize o banco antes de executar o backup."
        )
        LOGGER.error(msg)
        raise FileNotFoundError(msg)
    backup_dir = settings.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"info_ai_studio_{timestamp}.db"
    shutil.copy(db_path, backup_path)
    LOGGER.info("Backup gerado em %s", backup_path)
    return backup_path
