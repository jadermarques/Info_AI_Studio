"""Domain services for registering sources and channels."""

from __future__ import annotations

from typing import Any

from app.domain.entities import WebSource, YouTubeChannel
from app.domain import validators
from app.infrastructure import repositories


def register_youtube_channel(channel: YouTubeChannel) -> None:
    """Persist YouTube channel metadata."""

    channel_id = validators.normalize_channel_id(channel.canal_id)
    repositories.save_youtube_channel(
        nome_canal=channel.nome,
        descricao=channel.descricao,
        grupo=channel.grupo,
        canal_id=channel_id,
        status=1 if channel.status else 0,
    )


def list_youtube_channels(active_only: bool = True) -> list[dict[str, Any]]:
    """Return stored channels."""

    return repositories.list_youtube_channels(active_only=active_only)


def register_web_source(source: WebSource) -> None:
    """Persist a new web source using domain validations."""

    validators.validate_fonte_web(source.tipo, source.fonte)
    repositories.save_web_source(
        tipo=source.tipo,
        fonte=source.fonte,
        descricao=source.descricao,
        status=1 if source.status else 0,
    )


def list_web_sources(active_only: bool = True) -> list[dict[str, Any]]:
    """Return stored web sources."""

    return repositories.list_web_sources(active_only=active_only)
