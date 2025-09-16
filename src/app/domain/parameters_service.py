"""Domain services for configurable parameters stored in .env."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from app.config import reload_settings
from app.infrastructure.env_manager import update_env_values


def update_parameters(values: Mapping[str, str]) -> Path:
    """Persist parameters to the .env file and reload application settings."""

    path = update_env_values(values)
    reload_settings()
    return path
