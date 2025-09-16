"""Typer CLI for Info_AI_Studio."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from app.config import get_settings
from app.domain.entities import LLMModel, YouTubeExtractionConfig
from app.domain.llm_service import register_llm_model
from app.domain.youtube.service import YouTubeExecutionService
from app.infrastructure.backup import create_backup
from app.infrastructure.db import initialize_database, is_database_initialized
from app.infrastructure.logging_setup import setup_logging

app = typer.Typer(help="CLI principal do Info_AI_Studio")

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


@app.callback()
def cli_callback() -> None:
    """Inicializa logging padrão para todos os comandos."""

    setup_logging()


@app.command("db-init")
def db_init() -> None:
    """Inicializa o banco de dados executando o schema.sql."""

    initialize_database()
    typer.echo("Banco inicializado com sucesso.")


@app.command("db-backup")
def db_backup() -> None:
    """Gera um backup do banco SQLite na pasta configurada."""

    path = create_backup()
    typer.echo(f"Backup gerado em: {path}")


@app.command("modelo-ia")
def modelo_ia(
    provedor: str = typer.Option(..., "--provedor", help="Nome do provedor do modelo."),
    modelo: str = typer.Option(..., "--modelo", help="Nome do modelo LLM."),
    api_key: str = typer.Option(..., "--api-key", help="Chave de API para acesso ao modelo."),
    ativo: bool = typer.Option(True, "--ativo/--inativo", help="Define se o modelo está ativo."),
) -> None:
    """Cadastra ou atualiza um modelo LLM."""

    register_llm_model(LLMModel(provedor=provedor, modelo=modelo, api_key=api_key, status=ativo))
    typer.echo(f"Modelo {provedor}/{modelo} cadastrado com sucesso.")


@app.command("youtube-exec")
def youtube_exec(
    outdir: Optional[Path] = typer.Option(None, "--outdir", help="Diretório de saída."),
    prefix: str = typer.Option("youtube_extraction", "--prefix", help="Prefixo dos arquivos."),
    days: Optional[int] = typer.Option(3, "-d", "--days", help="Janela de dias para filtrar vídeos."),
    channels_file: Optional[Path] = typer.Option(
        None, "--channels-file", help="Arquivo com lista de canais (um por linha)."
    ),
    channel: List[str] = typer.Option(
        [], "-c", "--channel", help="Canal individual para análise (pode repetir)."
    ),
    no_asr: bool = typer.Option(False, "--no-asr", help="Desabilita o fallback de ASR."),
    asr_provider: str = typer.Option(
        "faster-whisper",
        "--asr-provider",
        help="Fornecedor de ASR para fallback.",
    ),
    model: Optional[str] = typer.Option(None, "--model", help="Modelo LLM para análises."),
    openai_key: Optional[str] = typer.Option(None, "--openai-key", help="Sobrescreve a chave da API."),
    resumo_max_palavras: Optional[int] = typer.Option(
        None, "--resumo-max-palavras", help="Limite de palavras para o resumo."),
    mode: str = typer.Option(
        "full", "-m", "--mode", help="Modo de execução (full ou simple)."
    ),
    no_llm: bool = typer.Option(False, "--no-llm", help="Ignora análises via LLM."),
    cookies: Optional[Path] = typer.Option(
        None, "--cookies", help="Arquivo de cookies no formato Netscape."
    ),
    user_agent: str = typer.Option(DEFAULT_USER_AGENT, "--user-agent", help="User-Agent usado nas requisições."),
    report_format: str = typer.Option(
        "txt", "--format", help="Formato do relatório (txt, json, pdf, html)."
    ),
    max_videos: Optional[int] = typer.Option(
        None, "--max-videos", help="Limita a quantidade de vídeos por canal."
    ),
) -> None:
    """Executa a extração de canais do YouTube."""

    settings = get_settings()
    output_dir = (outdir or settings.resultados_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    mode_normalized = mode.lower()
    if mode_normalized not in {"full", "simple"}:
        typer.echo("Modo inválido. Use 'full' ou 'simple'.")
        raise typer.Exit(code=1)
    provider_normalized = asr_provider.lower()
    if provider_normalized not in {"faster-whisper", "openai"}:
        typer.echo("Fornecedor de ASR inválido. Use 'faster-whisper' ou 'openai'.")
        raise typer.Exit(code=1)
    report_format_normalized = report_format.lower()
    if report_format_normalized not in {"txt", "json", "pdf", "html"}:
        typer.echo("Formato inválido. Use txt, json, pdf ou html.")
        raise typer.Exit(code=1)
    config = YouTubeExtractionConfig(
        outdir=output_dir,
        prefix=prefix,
        days=days,
        channels=channel,
        channels_file=channels_file,
        mode=mode_normalized,
        no_llm=no_llm,
        asr_enabled=not no_asr,
        asr_provider=provider_normalized,
        llm_model=model or settings.llm_model,
        llm_key=openai_key,
        resumo_max_palavras=resumo_max_palavras or settings.max_palavras_resumo,
        cookies=cookies or settings.cookies_path,
        user_agent=user_agent,
        report_format=report_format_normalized,
        max_videos=max_videos,
    )
    if not is_database_initialized():
        typer.echo("Banco de dados não inicializado. Execute 'app db-init' antes de prosseguir.")
        raise typer.Exit(code=1)
    service = YouTubeExecutionService(config)
    result = service.run()
    typer.echo("Extração concluída.")
    typer.echo(f"JSON: {result.json_path}")
    if result.report_path:
        typer.echo(f"Relatório: {result.report_path}")
    typer.echo(f"Log: {result.log_path}")
    typer.echo(
        f"Totais — canais: {result.total_channels}, vídeos: {result.total_videos}."
    )


if __name__ == "__main__":
    app()
