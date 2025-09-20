"""Domain services for registering sources and channels."""

from __future__ import annotations

from typing import Any

from app.domain.entities import WebSource, YouTubeChannel
from app.domain import validators
from app.infrastructure import repositories
from app.domain.youtube.groups import serialize_channel_groups


def register_youtube_channel(channel: YouTubeChannel) -> None:
    """Persist YouTube channel metadata (insert or update)."""

    channel_id = validators.normalize_channel_id(channel.canal_id)
    if channel.registro_id is not None:
        repositories.update_youtube_channel(
            entry_id=channel.registro_id,
            nome_canal=channel.nome,
            descricao=channel.descricao,
            grupos=serialize_channel_groups(channel.grupos),
            canal_id=channel_id,
            status=1 if channel.status else 0,
        )
    else:
        repositories.save_youtube_channel(
            nome_canal=channel.nome,
            descricao=channel.descricao,
            grupos=serialize_channel_groups(channel.grupos),
            canal_id=channel_id,
            status=1 if channel.status else 0,
        )


def list_youtube_channels(active_only: bool = True) -> list[dict[str, Any]]:
    """Return stored channels."""

    return repositories.list_youtube_channels(active_only=active_only)


def delete_youtube_channel(entry_id: int) -> None:
    """Remove a stored YouTube channel."""

    repositories.delete_youtube_channel(entry_id)


def register_web_source(source: WebSource, entry_id: int | None = None) -> None:
    """Persist or update a web source using domain validations."""

    validators.validate_fonte_web(source.tipo, source.fonte)
    if entry_id is not None:
        repositories.update_web_source(
            entry_id=entry_id,
            tipo=source.tipo,
            fonte=source.fonte,
            descricao=source.descricao,
            status=1 if source.status else 0,
        )
    else:
        repositories.save_web_source(
            tipo=source.tipo,
            fonte=source.fonte,
            descricao=source.descricao,
            status=1 if source.status else 0,
        )


def list_web_sources(active_only: bool = True) -> list[dict[str, Any]]:
    return repositories.list_web_sources(active_only=active_only)

def delete_web_source(entry_id: int) -> None:
    repositories.delete_web_source(entry_id)
