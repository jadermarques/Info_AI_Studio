"""Utilities for handling predefined YouTube channel groups."""

from __future__ import annotations

import re
from typing import Iterable

# Lista de grupos disponíveis para classificação dos canais do YouTube.
YOUTUBE_CHANNEL_GROUP_OPTIONS: list[str] = [
    "Ideias e Negócios com IA",
    "Notícias e Novidades em IA",
    "Tendências em IA",
    "Informações Big Techs IA",
    "Ferramentas de IA",
    "Pesquisas em IA",
    "Influenciadores IA",
    "Crítica/Opinião sobre IA",
    "Ética/Regulamentação/Segurança IA",
]

_GROUP_SEPARATOR = ";"

def normalize_channel_groups(groups: Iterable[str]) -> list[str]:
    """Return a sorted list with unique, trimmed group names."""

    unique = {group.strip() for group in groups if group and group.strip()}
    return sorted(unique)


def serialize_channel_groups(groups: Iterable[str]) -> str:
    """Serialize the list of groups to be stored in the database."""

    normalized = normalize_channel_groups(groups)
    return _GROUP_SEPARATOR.join(normalized)


def split_channel_groups(raw_groups: str | None) -> list[str]:
    """Split raw group data (from the database) into a list of names."""

    if not raw_groups:
        return []
    parts = re.split(r"[;|,]", raw_groups)
    return [part.strip() for part in parts if part and part.strip()]


def format_channel_groups(raw_groups: str | None) -> str:
    """Human readable representation of channel groups."""

    return ", ".join(split_channel_groups(raw_groups))

