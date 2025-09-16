"""Domain entities used throughout the application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class LLMModel:
    """Representa um modelo LLM disponível."""

    provedor: str
    modelo: str
    api_key: str
    status: bool = True
    model_id: int | None = None


@dataclass(slots=True)
class YouTubeChannel:
    """Informações básicas de um canal do YouTube."""

    nome: str
    descricao: str
    grupo: str
    canal_id: str
    status: bool = True


@dataclass(slots=True)
class WebSource:
    """Fonte web cadastrada."""

    tipo: str
    fonte: str
    descricao: str
    status: bool = True


@dataclass(slots=True)
class YouTubeExtractionConfig:
    """Parâmetros para execução da extração do YouTube."""

    outdir: Path
    prefix: str
    days: Optional[int]
    channels: list[str]
    channels_file: Optional[Path]
    mode: str
    no_llm: bool
    asr_enabled: bool
    asr_provider: str
    llm_provider: Optional[str]
    llm_model: str
    llm_key: Optional[str]
    resumo_max_palavras: int
    cookies: Optional[Path]
    user_agent: str
    report_format: str
    max_videos: Optional[int]


@dataclass(slots=True)
class YouTubeExtractionResult:
    """Resultado da execução da extração do YouTube."""

    json_path: Optional[Path]
    report_path: Optional[Path]
    log_path: Optional[Path]
    total_videos: int
    total_channels: int
    message: str
    token_details: list[dict[str, int | str]]
    channel_tokens: list[dict[str, int | str]]
    total_prompt_tokens: int
    total_completion_tokens: int
