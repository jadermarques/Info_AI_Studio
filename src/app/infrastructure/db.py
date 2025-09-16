"""SQLite helpers for the application."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterable, Sequence

from app.config import get_settings


@contextmanager
def get_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Return a context manager for sqlite3 connections."""

    settings = get_settings()
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(schema_path: Path | None = None) -> None:
    """Create database tables if they do not exist."""

    settings = get_settings()
    schema_file = schema_path or Path(__file__).with_name("schema.sql")
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    sql = schema_file.read_text(encoding="utf-8")
    with get_connection(settings.db_path) as conn:
        conn.executescript(sql)


def is_database_initialized() -> bool:
    """Check if the base tables exist."""

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                ("modelo_llm",),
            )
            return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def execute(query: str, params: Sequence[Any] | None = None) -> None:
    """Execute a write query."""

    with get_connection() as conn:
        conn.execute(query, params or [])


def executemany(query: str, params: Iterable[Sequence[Any]]) -> None:
    """Execute a write query for multiple parameter sets."""

    with get_connection() as conn:
        conn.executemany(query, list(params))


def fetch_all(query: str, params: Sequence[Any] | None = None) -> list[sqlite3.Row]:
    """Return all rows for a query."""

    with get_connection() as conn:
        cur = conn.execute(query, params or [])
        return cur.fetchall()


def fetch_one(query: str, params: Sequence[Any] | None = None) -> sqlite3.Row | None:
    """Return a single row for a query."""

    with get_connection() as conn:
        cur = conn.execute(query, params or [])
        return cur.fetchone()
