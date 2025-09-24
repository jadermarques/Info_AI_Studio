"""Central logging configuration for the application.

Recursos:
- Handler rotativo por tamanho (padrão 10MB), com backups configuráveis
- Nível custom "FULL" (15) para rastrear ações de UI/eventos granulares
- Helper para registrar eventos de interface
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

from app.config import get_settings

FULL_LOG_LEVEL = 15
logging.addLevelName(FULL_LOG_LEVEL, "FULL")


def _log_full(self: logging.Logger, message: str, *args, **kwargs) -> None:
    if self.isEnabledFor(FULL_LOG_LEVEL):
        self._log(FULL_LOG_LEVEL, message, args, **kwargs)


if not hasattr(logging.Logger, "full"):
    logging.Logger.full = _log_full  # type: ignore[attr-defined]


class _TypesFilter(logging.Filter):
    def __init__(self, allowed: set[int]) -> None:
        super().__init__()
        self.allowed = allowed

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        return record.levelno in self.allowed


def _allowed_levels_from_settings() -> tuple[set[int], int]:
    settings = get_settings()
    types = {t.strip() for t in (settings.log_types or "").split(",") if t.strip()}
    allowed: set[int] = set()
    # Map tipos → níveis
    if "error" in types:
        allowed.add(logging.ERROR)
    if "warning" in types:
        allowed.add(logging.WARNING)
    if "info" in types:
        allowed.add(logging.INFO)
    if "debug" in types:
        allowed.add(logging.DEBUG)
    if "full" in types:
        allowed.add(FULL_LOG_LEVEL)
    # Se nenhum tipo informado, default INFO+WARNING+ERROR
    if not allowed:
        allowed = {logging.INFO, logging.WARNING, logging.ERROR}
    min_level = min(allowed)
    return allowed, min_level


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """Configure root logging with console and optional rotating file handler."""

    logger = logging.getLogger()
    allowed, min_level = _allowed_levels_from_settings()
    numeric_level = min(min_level, getattr(logging, level.upper(), logging.INFO))
    logger.setLevel(numeric_level)
    types_filter = _TypesFilter(allowed)
    # Console handler (cria se não existir)
    console = None
    for h in logger.handlers:
        if isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler):
            console = h
            break
    if console is None:
        console = logging.StreamHandler()
        logger.addHandler(console)
    console.setLevel(numeric_level)
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    console.filters = [types_filter]
    if log_file is not None:
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_file):
                break
        else:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            settings = get_settings()
            max_bytes = max(1, settings.log_rotate_max_mb) * 1024 * 1024
            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=max(1, settings.log_backup_count), encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
            )
            logger.addHandler(file_handler)
    # Atualiza filtros e níveis em todos os handlers
    for h in logger.handlers:
        h.setLevel(numeric_level)
        h.addFilter(types_filter)
    return logger


def get_log_file_path(filename: str) -> Path:
    """Return a path inside the configured log directory."""

    settings = get_settings()
    return settings.log_dir / filename


def ui_event(logger: Optional[logging.Logger], action: str, **kwargs) -> None:
    """Loga um evento de UI no nível FULL com payload adicional.

    Exemplos:
      ui_event(LOGGER, "click", button="Executar", page="Execução/YouTube")
    """
    if logger is None:
        logger = logging.getLogger("app.ui")
    payload = {k: v for k, v in kwargs.items()}
    try:
        import json
        extra_txt = json.dumps(payload, ensure_ascii=False)
    except Exception:
        extra_txt = str(payload)
    logger.full(f"UI_EVENT {action} {extra_txt}")
