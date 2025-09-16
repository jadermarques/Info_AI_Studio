"""Domain level validations for inputs."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from app.infrastructure import repositories


_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_valid_url(value: str) -> bool:
    """Validate basic structure of an URL."""

    if not value:
        return False
    if not _URL_RE.match(value.strip()):
        return False
    parsed = urlparse(value)
    return all([parsed.scheme, parsed.netloc])


def validate_fonte_web(tipo: str, fonte: str) -> None:
    """Validate source rules based on type."""

    tipo_norm = tipo.lower().strip()
    fonte_norm = fonte.strip()
    if tipo_norm in {"site", "blog"} and not is_valid_url(fonte_norm):
        raise ValueError("O campo 'fonte' deve conter uma URL completa para sites/blogs.")
    if tipo_norm == "youtube":
        if not repositories.get_youtube_channel_by_id(fonte_norm):
            raise ValueError(
                "Canal não encontrado. Cadastre o canal do YouTube antes de usá-lo como fonte."
            )


def normalize_channel_id(channel: str) -> str:
    """Normalize a channel identifier to start with @ when missing."""

    channel = channel.strip()
    if channel and not channel.startswith("@") and not channel.startswith("UC"):
        return f"@{channel}"
    return channel