"""Database repositories for domain entities."""

from __future__ import annotations

from typing import Any, Iterable

from app.infrastructure import db


def save_llm_model(provedor: str, modelo: str, api_key: str, status: int = 1) -> None:
    """Insert or update a registered LLM model."""

    query = (
        "INSERT INTO modelo_llm (modl_provedor, modl_modelo_llm, modl_api_key, modl_status)"
        " VALUES (?, ?, ?, ?)"
        " ON CONFLICT(modl_provedor, modl_modelo_llm) DO UPDATE SET"
        " modl_api_key = excluded.modl_api_key,"
        " modl_status = excluded.modl_status"
    )
    db.execute(query, (provedor.strip(), modelo.strip(), api_key.strip(), status))


def list_llm_models() -> list[dict[str, Any]]:
    """Return registered LLM models."""

    rows = db.fetch_all(
        "SELECT modl_id, modl_provedor, modl_modelo_llm, modl_api_key, modl_status, modl_created_at"
        " FROM modelo_llm ORDER BY modl_created_at DESC"
    )
    return [dict(row) for row in rows]


def save_youtube_channel(
    nome_canal: str,
    descricao: str,
    grupo: str,
    canal_id: str,
    status: int = 1,
) -> None:
    """Insert or update a YouTube channel entry."""

    query = (
        "INSERT INTO fonte_youtube (foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal, foyt_status)"
        " VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(foyt_id_canal) DO UPDATE SET"
        " foyt_nome_canal = excluded.foyt_nome_canal,"
        " foyt_descricao = excluded.foyt_descricao,"
        " foyt_grupo_canal = excluded.foyt_grupo_canal,"
        " foyt_status = excluded.foyt_status"
    )
    db.execute(query, (nome_canal.strip(), descricao.strip(), grupo.strip(), canal_id.strip(), status))


def list_youtube_channels(active_only: bool = True) -> list[dict[str, Any]]:
    """Return registered YouTube channels."""

    query = (
        "SELECT foyt_id, foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal,"
        " foyt_status, foyt_created_at"
        " FROM fonte_youtube"
    )
    params: Iterable[Any] = ()
    if active_only:
        query += " WHERE foyt_status = 1"
    query += " ORDER BY foyt_nome_canal ASC"
    rows = db.fetch_all(query, params)
    return [dict(row) for row in rows]


def get_youtube_channel_by_id(channel_id: str) -> dict[str, Any] | None:
    """Return channel data by the stored channel id."""

    row = db.fetch_one(
        "SELECT foyt_id, foyt_nome_canal, foyt_descricao, foyt_grupo_canal, foyt_id_canal,"
        " foyt_status FROM fonte_youtube WHERE foyt_id_canal = ?",
        (channel_id,),
    )
    return dict(row) if row else None


def save_web_source(
    tipo: str,
    fonte: str,
    descricao: str,
    status: int = 1,
) -> None:
    """Insert a new web source."""

    query = (
        "INSERT INTO fonte_web (fowe_tipo, fowe_fonte, fowe_descricao, fowe_status)"
        " VALUES (?, ?, ?, ?)"
    )
    db.execute(query, (tipo.strip(), fonte.strip(), descricao.strip(), status))


def list_web_sources(active_only: bool = True) -> list[dict[str, Any]]:
    """Return registered web sources."""

    query = (
        "SELECT fowe_id, fowe_tipo, fowe_fonte, fowe_descricao, fowe_status, fowe_created_at"
        " FROM fonte_web"
    )
    if active_only:
        query += " WHERE fowe_status = 1"
    query += " ORDER BY fowe_created_at DESC"
    rows = db.fetch_all(query)
    return [dict(row) for row in rows]


def record_youtube_extraction(
    channel_label: str,
    mode: str,
    json_path: str | None,
    report_path: str | None,
    log_path: str | None,
    total_videos: int,
    total_channels: int,
) -> None:
    """Persist metadata for a YouTube extraction run."""

    query = (
        "INSERT INTO youtube_extraction (ytex_channel, ytex_mode, ytex_json_path, ytex_report_path,"
        " ytex_log_path, ytex_total_videos, ytex_total_channels)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    db.execute(
        query,
        (
            channel_label,
            mode,
            json_path,
            report_path,
            log_path,
            total_videos,
            total_channels,
        ),
    )


def list_youtube_extractions(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent extraction runs."""

    rows = db.fetch_all(
        "SELECT ytex_id, ytex_channel, ytex_mode, ytex_created_at, ytex_json_path, ytex_report_path,"
        " ytex_log_path, ytex_total_videos, ytex_total_channels"
        " FROM youtube_extraction ORDER BY ytex_created_at DESC LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in rows]