from __future__ import annotations

import os
import tempfile
from pathlib import Path
import sqlite3
import pytest

from app.config import reload_settings, get_settings
from app.infrastructure.db import initialize_database, get_connection


@pytest.fixture(autouse=True)
def temp_db_env(monkeypatch: pytest.MonkeyPatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        monkeypatch.setenv("DB_PATH", str(db_path))
        reload_settings()
        initialize_database()
        yield
        # Fecha conexões pendentes e remove arquivo se existir
        try:
            with get_connection() as conn:
                conn.close()
        except Exception:
            pass
        if db_path.exists():
            try:
                db_path.unlink()
            except Exception:
                pass
