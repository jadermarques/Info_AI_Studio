"""Smoke tests for basic infrastructure."""

from __future__ import annotations

from app.config import reload_settings
from app.infrastructure.db import get_connection, initialize_database


def test_initialize_and_insert(tmp_path, monkeypatch) -> None:
    """Ensure the database schema can be created and used."""

    db_path = tmp_path / "data.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    reload_settings()
    initialize_database()
    assert db_path.exists()
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO modelo_llm (modl_provedor, modl_modelo_llm, modl_api_key) VALUES (?, ?, ?)",
            ("TEST", "model", "key"),
        )
        cursor = conn.execute("SELECT COUNT(*) FROM modelo_llm")
        assert cursor.fetchone()[0] == 1