"""Typer CLI for Info_AI_Studio."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import typer

from app.config import get_settings
from app.domain.entities import LLMModel, YouTubeExtractionConfig, YouTubeExtractionResult
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


def _pluralize_days(value: Optional[int]) -> str:
    if value is None:
        return "N/A"
    return f"{value} dia" + ("" if value == 1 else "s")


def _build_header_lines(
    start_time: datetime,
    config: YouTubeExtractionConfig,
    channels_file: Optional[Path],
    settings_api_key: str,
) -> List[str]:
    effective_key = config.llm_key or settings_api_key or "N/A"
    days_label = _pluralize_days(config.days)
    file_label = str(channels_file) if channels_file else "N/A"
    return [
        "Iniciando execução do YouTubeChannelAnalyzer",
        "",
        f"Data: {start_time.date()}",
        "",
        f"Hora: {start_time.strftime('%H:%M:%S')}",
        "",
        "Parâmetros utilizados:",
        f" • Dias para filtrar vídeos recente(-d): {days_label}",
        f" • Arquivo de canais (-f): {file_label}",
        f" • Prefixo para arquivos de saída (--prefix): {config.prefix}",
        "",
        f" Modelo LLM: {config.llm_model}",
        "",
        f" API Key: {effective_key}",
        "",
    ]


def _format_video_date(video: dict) -> str:
    iso = (video.get("date_published") or video.get("published") or "").strip()
    relative = (video.get("published_relative") or "").strip()
    iso_short = iso[:10] if iso else ""
    if iso_short and relative:
        return f"{iso_short} ({relative})"
    if iso_short:
        return iso_short
    if relative:
        return relative
    return "sem data"


def _format_summary_section(result: YouTubeExtractionResult) -> str:
    lines: List[str] = []
    lines.append("========================================================================")
    lines.append("📊 RESUMO DA EXTRAÇÃO")
    lines.append("========================================================================")
    lines.append("")
    lines.append("📈 Estatísticas Gerais:")
    lines.append(f"   • Canais processados: {result.total_channels}")
    lines.append(f"   • Canais bem-sucedidos: {result.success_channels}")
    lines.append(f"   • Canais com falha: {result.failed_channels}")
    success_rate = (
        result.success_channels / result.total_channels * 100.0
        if result.total_channels
        else 0.0
    )
    lines.append(f"   • Taxa de sucesso: {success_rate:.1f}%")
    lines.append(f"   • Total de requisições: {result.total_requests}")
    lines.append(f"   • Tempo de extração: {result.started_at.isoformat()}")
    lines.append("")
    lines.append("📺 Detalhes por Canal:")
    for channel in result.channels_data:
        status = "✅" if channel.get("status") == "success" else "❌"
        name = channel.get("name") or channel.get("channel_id") or "Canal"
        lines.append(f"   {status} {name}")
        lines.append(f"      ID: {channel.get('channel_id', '')}")
        subscribers = channel.get("subscriber_count") or "N/A"
        lines.append(f"      Inscritos: {subscribers if subscribers else 'N/A'}")
        videos = channel.get("videos") or []
        lines.append(f"      Vídeos extraídos: {len(videos)}")
        if videos:
            lines.append("      • Vídeos encontrados:")
            for video in videos:
                title = (video.get("title") or "").strip()
                lines.append(f"         - {title} — {_format_video_date(video)}")
        lines.append("")
    lines.append(f"🎥 Total de vídeos extraídos: {result.total_videos}")
    lines.append("========================================================================")
    lines.append("")
    lines.append(
        "✨ Extração concluída com sucesso!"
        if result.failed_channels == 0
        else "✨ Extração concluída com pendências."
    )
    return "\n".join(lines)


def _format_video_details(result: YouTubeExtractionResult) -> str:
    lines: List[str] = ["DETALHE DOS VÍDEOS", "------------------------------------------------------------------------"]
    resumo_limite = result.params.get("resumo_max_palavras") if result.params else None
    for channel in result.channels_data:
        channel_name = channel.get("name") or channel.get("channel_id") or ""
        for video in channel.get("videos") or []:
            summary = video.get("summary") or {}
            keywords = summary.get("palavras_chave") or []
            if isinstance(keywords, str):
                keywords = [item.strip() for item in keywords.split(",") if item.strip()]
            topics = (summary.get("resumo_em_topicos") or "").strip()
            lines.append(f"• {channel_name}")
            lines.append(f"   - URL: {video.get('url', '')}")
            lines.append(f"   - Título: {video.get('title', '')}")
            lines.append(f"   - Duração: {video.get('duration') or 'N/A'}")
            lines.append(f"   - Data de postagem: {video.get('date_published') or video.get('published') or video.get('published_relative') or ''}")
            lines.append(f"   - Assunto principal: {summary.get('assunto_principal', '')}")
            lines.append(f"   - Resumo (1 frase): {summary.get('resumo_uma_frase', '')}")
            limite_txt = resumo_limite if resumo_limite is not None else 0
            lines.append(
                f"   - Resumo (<= {limite_txt} palavras): {summary.get('resumo', '')}"
            )
            lines.append(
                "   - Palavras-chave: " + (", ".join(keywords) if keywords else "")
            )
            lines.append(f"   - Resumo em tópicos:\n{topics}")
            model_name = summary.get("model") or result.params.get("llm_model") if result.params else ""
            lines.append(f"   - Modelo LLM: {model_name}")
            lines.append(f"   - Tokens enviados: {summary.get('prompt_tokens', 0)}")
            lines.append(f"   - Tokens recebidos: {summary.get('completion_tokens', 0)}")
            cost_value = summary.get("cost", 0.0) or 0.0
            lines.append(f"   - Custo estimado: R$ {float(cost_value):.4f}")
            lines.append("")
    return "\n".join(lines)


def _format_llm_usage(result: YouTubeExtractionResult) -> str:
    lines: List[str] = [
        "========================================================================",
        "📊 RESUMO DE USO DE LLMs",
        "========================================================================",
        "",
    ]
    if not result.token_details:
        lines.append("Nenhuma chamada LLM registrada.")
        lines.append("========================================================================")
        return "\n".join(lines)
    modelos: dict[str, dict[str, float]] = {}
    canais: dict[str, dict[str, object]] = {}
    custo_total = 0.0
    for detail in result.token_details:
        modelo = str(detail.get("modelo") or result.params.get("llm_model") if result.params else "")
        prompt_tokens = int(detail.get("tokens_entrada") or 0)
        completion_tokens = int(detail.get("tokens_saida") or 0)
        custo = float(detail.get("custo_estimado") or 0.0)
        custo_total += custo
        data_modelo = modelos.setdefault(modelo, {"prompt": 0, "completion": 0, "custo": 0.0})
        data_modelo["prompt"] += prompt_tokens
        data_modelo["completion"] += completion_tokens
        data_modelo["custo"] += custo
        canal_nome = str(detail.get("canal") or "")
        canal_info = canais.setdefault(canal_nome, {"custo": 0.0, "videos": []})
        canal_info["custo"] += custo
        canal_info.setdefault("videos", []).append(
            {
                "video_id": detail.get("video_id") or detail.get("video") or "",
                "modelo": modelo,
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "custo": custo,
            }
        )
    lines.append("Modelos:")
    for modelo, info in modelos.items():
        lines.append(
            f"  - {modelo}: enviados={int(info['prompt'])} tokens, recebidos={int(info['completion'])} tokens, custo R$ {info['custo']:.4f}"
        )
    lines.append("")
    lines.append("Custos por canal:")
    for canal_nome, info in canais.items():
        lines.append(f"  {canal_nome}: R$ {float(info['custo']):.4f}")
        for video_info in info["videos"]:  # type: ignore[index]
            lines.append(
                f"     • Vídeo {video_info['video_id']}: modelo={video_info['modelo']}, enviados={video_info['prompt']} tokens, recebidos={video_info['completion']} tokens, custo R$ {video_info['custo']:.4f}"
            )
    lines.append("")
    lines.append(f"Custo total estimado: R$ {custo_total:.4f}")
    lines.append("========================================================================")
    return "\n".join(lines)


def _format_footer(result: YouTubeExtractionResult) -> List[str]:
    lines: List[str] = []
    if result.report_path:
        lines.append(f"   📄 Relatório salvo em: {result.report_path}")
    if result.json_path:
        lines.append(f"   📄 Arquivo de resultados: {result.json_path.name}")
        lines.append(f"   📁 Diretório: {result.json_path.parent}")
    if result.log_path:
        lines.append(f"   📝 Log completo: {result.log_path}")
    return lines


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
        "txt", "--format", help="Formato do relatório (txt, md, json, pdf, html)."
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
    if report_format_normalized not in {"txt", "md", "json", "pdf", "html"}:
        typer.echo("Formato inválido. Use txt, md, json, pdf ou html.")
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
        llm_provider=settings.llm_provider,
        llm_model=model or settings.llm_model,
        llm_key=openai_key,
        resumo_max_palavras=resumo_max_palavras or settings.max_palavras_resumo,
        cookies=cookies or settings.cookies_path,
        user_agent=user_agent,
        report_format=report_format_normalized,
        max_videos=max_videos,
        translate_results=settings.translate_results,
    )
    if not is_database_initialized():
        typer.echo("Banco de dados não inicializado. Execute 'app db-init' antes de prosseguir.")
        raise typer.Exit(code=1)
    header_time = datetime.now()
    for line in _build_header_lines(header_time, config, channels_file, settings.llm_api_key):
        typer.echo(line)
    service = YouTubeExecutionService(config)
    result = service.run()
    size_bytes = 0
    if result.json_path and result.json_path.exists():
        size_bytes = result.json_path.stat().st_size
    typer.echo("")
    typer.echo("💾 Salvando resultados...")
    if result.json_path:
        typer.echo(f"💾 Resultados salvos em: {result.json_path}")
        typer.echo(f"   📊 Tamanho do arquivo: {size_bytes:,} bytes")
    typer.echo("")
    typer.echo(_format_summary_section(result))
    typer.echo("")
    typer.echo(_format_video_details(result))
    typer.echo(_format_llm_usage(result))
    for line in _format_footer(result):
        typer.echo(line)


if __name__ == "__main__":
    app()
