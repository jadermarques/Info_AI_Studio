"""Application configuration helpers."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:  # pragma: no cover - optional dependency during tests
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore[override]
        return False


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    db_path: Path
    max_palavras_resumo: int
    llm_provider: str
    llm_model: str
    llm_api_key: str
    token_limit: int
    resultados_dir: Path
    backup_dir: Path
    log_dir: Path
    cookies_path: Optional[Path]
    translate_results: str


def _load_env() -> None:
    """Load .env file values if available."""

    load_dotenv(override=False)


def _provider_env_var(provider: str) -> str:
    """Compute the provider-specific API key environment variable."""

    normalized = re.sub(r"[^A-Z0-9]+", "_", provider.strip().upper()).strip("_")
    return f"{normalized or 'LLM'}_API_KEY"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    _load_env()
    db_path = Path(os.getenv("DB_PATH", "./data.db")).expanduser().resolve()
    max_palavras = int(os.getenv("MAX_PALAVRAS_RESUMO", "150") or 150)
    llm_provider = os.getenv("LLM_PROVIDER", "OPENAI").strip()
    llm_model = os.getenv("LLM_MODEL", "gpt-5-nano").strip()
    provider_env_var = _provider_env_var(llm_provider)
    llm_api_key = os.getenv(provider_env_var, os.getenv("LLM_API_KEY", "")).strip()
    token_limit = int(os.getenv("TOKEN_LIMIT", "4096") or 4096)
    translate_raw = os.getenv("TRANSLATE_RESULTS", "original").strip().lower()
    translate_results = "pt-br" if translate_raw in {"pt", "pt-br", "pt_br", "portugues", "português", "br"} else "original"
    resultados_dir = Path(os.getenv("RESULTADOS_DIR", "resultados_extracao"))
    backup_dir = Path(os.getenv("BACKUP_DIR", "backup"))
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    cookies_env = os.getenv("COOKIES_PATH", "cookies.txt").strip()
    cookies_path = Path(cookies_env) if cookies_env else None
    return Settings(
        db_path=db_path,
        max_palavras_resumo=max_palavras,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        token_limit=token_limit,
        resultados_dir=resultados_dir,
        backup_dir=backup_dir,
        log_dir=log_dir,
        cookies_path=cookies_path,
        translate_results=translate_results,
    )


def reload_settings() -> None:
    """Clear cached configuration to reload updated environment variables."""

    get_settings.cache_clear()
