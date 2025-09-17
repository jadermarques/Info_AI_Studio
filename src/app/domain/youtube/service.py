"""Service orchestrating YouTube extractions."""

from __future__ import annotations

import html
import json
import logging
import tempfile
from dataclasses import asdict
from datetime import datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Callable, Optional

from fpdf import FPDF

from app.config import get_settings
from app.domain import validators
from app.domain.entities import YouTubeExtractionConfig, YouTubeExtractionResult
from app.domain.llm_client import LLMClient, LLMResult
from app.domain.youtube.extractor_plus import YouTubeExtractor
from app.infrastructure import repositories
from app.infrastructure.logging_setup import get_log_file_path, setup_logging

LOGGER = logging.getLogger(__name__)

ASR_LANG = "pt"
FASTER_WHISPER_MODEL = "small"
FASTER_WHISPER_COMPUTE = "auto"
OPENAI_WHISPER_MODEL = "whisper-1"


class YouTubeExecutionService:
    """Orchestrates the extraction workflow."""

    def __init__(self, config: YouTubeExtractionConfig) -> None:
        self.config = config
        self.settings = get_settings()
        self.resultados_dir = config.outdir.resolve()
        self.resultados_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self, progress_callback: Optional[Callable[[str], None]] = None
    ) -> YouTubeExtractionResult:
        """Execute the extraction and return metadata about generated files."""

        channels = self._resolve_channels()
        if not channels:
            raise ValueError("Nenhum canal informado ou cadastrado.")
        self._notify(progress_callback, f"{len(channels)} canais selecionados para análise.")
        timestamp = datetime.now()
        run_id = timestamp.strftime("%Y%m%d_%H%M%S")
        log_path = get_log_file_path(f"youtube_extraction_{run_id}.log")
        setup_logging(log_file=log_path)
        logger = logging.getLogger(f"app.youtube.run.{run_id}")
        logger.setLevel(logging.INFO)
        logger.propagate = True
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        )
        logger.addHandler(file_handler)

        logger.info("Iniciando extração em lote de %s canais", len(channels))
        self._notify(
            progress_callback,
            "Iniciando processamento dos canais selecionados...",
        )
        extractor = self._build_extractor()
        llm_client = self._build_llm_client()
        total_videos = 0
        channel_payload: list[dict] = []
        channel_tokens: list[dict[str, int | str]] = []
        token_details: list[dict[str, int | str]] = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        try:
            for index, channel in enumerate(channels, start=1):
                logger.info("Processando canal %s/%s: %s", index, len(channels), channel)
                self._notify(
                    progress_callback,
                    f"Processando canal {index}/{len(channels)}: {channel}",
                )
                info = extractor.extract_channel_info(channel)
                if info.get("status") != "success":
                    logger.warning("Falha ao extrair informações do canal %s", channel)
                    channel_payload.append({
                        "channel_id": channel,
                        "status": "error",
                        "message": info.get("message", "Falha ao extrair canal."),
                        "videos": [],
                    })
                    continue
                videos = extractor.extract_recent_videos(
                    channel,
                    max_age_days=self.config.days,
                    videos_tab_only=True,
                    max_videos=self.config.max_videos,
                )
                logger.info(
                    "Canal %s extraído com sucesso. Vídeos dentro do critério: %s",
                    channel,
                    len(videos),
                )
                self._notify(
                    progress_callback,
                    f"Canal {channel} com {len(videos)} vídeo(s) dentro do critério.",
                )
                enriched_videos = []
                prompt_tokens_channel = 0
                completion_tokens_channel = 0
                for video in videos:
                    video_id = video.get("id")
                    if not video_id:
                        continue
                    details = extractor.fetch_video_details(video_id)
                    transcript = ""
                    summary: Optional[LLMResult] = None
                    if self.config.mode.lower() == "full":
                        transcript = self._obter_transcricao(video_id, extractor, logger)
                        if transcript and not self.config.no_llm:
                            summary = llm_client.summarise(
                                title=video.get("title", ""),
                                transcript=transcript,
                                channel=info.get("name") or channel,
                                max_palavras=self.config.resumo_max_palavras,
                            )
                        elif self.config.no_llm:
                            logger.info(
                                "[LLM] Execução com --no-llm habilitado; resumos serão pulados."
                            )
                    prompt_tokens = summary.prompt_tokens if summary else 0
                    completion_tokens = summary.completion_tokens if summary else 0
                    prompt_tokens_channel += prompt_tokens
                    completion_tokens_channel += completion_tokens
                    token_details.append(
                        {
                            "canal": info.get("name") or channel,
                            "video": video.get("title", ""),
                            "tokens_entrada": prompt_tokens,
                            "tokens_saida": completion_tokens,
                            "tokens_totais": prompt_tokens + completion_tokens,
                        }
                    )
                    summary_payload = asdict(summary) if summary else None
                    enriched_videos.append(
                        {
                            "id": video_id,
                            "title": video.get("title"),
                            "url": video.get("url"),
                            "published": video.get("published"),
                            "published_relative": video.get("published_relative"),
                            "duration": details.get("duration_hhmmss"),
                            "date_published": details.get("date_published"),
                            "transcript_available": bool(transcript),
                            "transcript": transcript if self.config.mode.lower() == "full" else "",
                            "summary": summary_payload,
                        }
                    )
                total_videos += len(enriched_videos)
                channel_payload.append(
                    {
                        "channel_id": channel,
                        "name": info.get("name", channel),
                        "subscriber_count": info.get("subscriber_count"),
                        "description": info.get("description"),
                        "video_count": info.get("video_count"),
                        "videos": enriched_videos,
                        "status": "success",
                    }
                )
                channel_tokens.append(
                    {
                        "canal": info.get("name") or channel,
                        "tokens_entrada": prompt_tokens_channel,
                        "tokens_saida": completion_tokens_channel,
                        "tokens_totais": prompt_tokens_channel
                        + completion_tokens_channel,
                    }
                )
                total_prompt_tokens += prompt_tokens_channel
                total_completion_tokens += completion_tokens_channel
        finally:
            logger.removeHandler(file_handler)
            file_handler.close()

        json_path, report_path = self._persist_outputs(
            run_id, channel_payload, total_videos, timestamp
        )
        self._notify(
            progress_callback,
            "Extração finalizada. Resultados disponíveis para consulta.",
        )
        repositories.record_youtube_extraction(
            channel_label=", ".join(channels[:3]) + ("..." if len(channels) > 3 else ""),
            mode=self.config.mode,
            json_path=str(json_path) if json_path else None,
            report_path=str(report_path) if report_path else None,
            log_path=str(log_path),
            total_videos=total_videos,
            total_channels=len(channel_payload),
        )
        message = (
            "Extração concluída com sucesso" if channel_payload else "Nenhum resultado gerado"
        )
        return YouTubeExtractionResult(
            json_path=json_path,
            report_path=report_path,
            log_path=log_path,
            total_videos=total_videos,
            total_channels=len(channel_payload),
            message=message,
            token_details=token_details,
            channel_tokens=channel_tokens,
            total_prompt_tokens=total_prompt_tokens,
            total_completion_tokens=total_completion_tokens,
        )

    def _resolve_channels(self) -> list[str]:
        """Return the list of channels considering CLI, files and database."""

        channels: list[str] = []
        for raw in self.config.channels:
            if raw:
                channels.append(validators.normalize_channel_id(raw))
        if self.config.channels_file and self.config.channels_file.exists():
            file_channels = self._load_channels_from_file(self.config.channels_file)
            channels.extend(file_channels)
        if not channels:
            db_channels = repositories.list_youtube_channels(active_only=True)
            channels = [validators.normalize_channel_id(c["foyt_id_canal"]) for c in db_channels]
        # remove duplicados mantendo ordem
        seen = set()
        deduped = []
        for ch in channels:
            if ch not in seen:
                deduped.append(ch)
                seen.add(ch)
        return deduped

    def _load_channels_from_file(self, path: Path) -> list[str]:
        """Read a channels file in the legacy format."""

        entries: list[str] = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                entries.append(validators.normalize_channel_id(line))
        except FileNotFoundError:
            LOGGER.warning("Arquivo de canais %s não encontrado.", path)
        return entries

    def _build_extractor(self) -> YouTubeExtractor:
        extractor = YouTubeExtractor(user_agent=self.config.user_agent)
        if self.config.cookies and self.config.cookies.exists():
            try:
                jar = MozillaCookieJar(str(self.config.cookies))
                jar.load(ignore_discard=True, ignore_expires=True)
                extractor.session.cookies.update(jar)
                LOGGER.info("Cookies carregados de %s", self.config.cookies)
            except Exception as exc:
                LOGGER.warning("Falha ao carregar cookies: %s", exc)
        return extractor

    def _build_llm_client(self) -> LLMClient:
        if self.config.no_llm:
            return LLMClient("none", self.settings.llm_model, None, self.settings.token_limit)
        api_key = self.config.llm_key or self.settings.llm_api_key
        model = self.config.llm_model or self.settings.llm_model
        provider = (self.config.llm_provider or self.settings.llm_provider or "").strip()
        return LLMClient(provider, model, api_key, self.settings.token_limit)

    @staticmethod
    def _notify(
        callback: Optional[Callable[[str], None]], message: str
    ) -> None:
        if callback:
            callback(message)

    def _obter_transcricao(
        self,
        video_id: str,
        extractor: YouTubeExtractor,
        logger: logging.Logger,
    ) -> str:
        text = extractor.fetch_transcript_text(video_id)
        if text:
            return text
        if not self.config.asr_enabled:
            logger.info("[ASR desativado] Sem transcrição YouTube para %s", video_id)
            return ""
        logger.info("[ASR ativado] Transcrição não encontrada; iniciando fallback para %s", video_id)
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = self._download_audio(video_id, Path(tmp_dir), logger)
            if not audio_path:
                return ""
            if self.config.asr_provider == "openai":
                return self._asr_openai(audio_path, logger)
            return self._asr_faster_whisper(audio_path, logger)

    def _download_audio(
        self, video_id: str, outdir: Path, logger: logging.Logger
    ) -> Optional[Path]:
        try:
            import yt_dlp
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("yt-dlp não disponível: %s", exc)
            return None
        outdir.mkdir(parents=True, exist_ok=True)
        options = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": str(outdir / f"{video_id}.%(ext)s"),
            "nocheckcertificate": True,
        }
        if self.config.cookies and self.config.cookies.exists():
            options["cookiefile"] = str(self.config.cookies.resolve())
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
                if "requested_downloads" in info and info["requested_downloads"]:
                    filepath = info["requested_downloads"][0].get("filepath")
                else:
                    filepath = ydl.prepare_filename(info)
            path = Path(filepath)
            if path.exists():
                logger.info("Áudio baixado para %s", path)
                return path
        except Exception as exc:  # pragma: no cover - heavy dependency
            logger.warning("yt-dlp falhou para %s: %s", video_id, exc)
        return None

    def _asr_faster_whisper(self, path: Path, logger: logging.Logger) -> str:
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("faster-whisper indisponível: %s", exc)
            return ""
        try:
            model = WhisperModel(
                FASTER_WHISPER_MODEL,
                device="auto",
                compute_type=FASTER_WHISPER_COMPUTE,
            )
            segments, _ = model.transcribe(str(path), language=ASR_LANG, vad_filter=True)
            return " ".join([getattr(seg, "text", "") for seg in segments if getattr(seg, "text", "")])
        except Exception as exc:  # pragma: no cover - heavy dependency
            logger.warning("faster-whisper falhou: %s", exc)
            return ""

    def _asr_openai(self, path: Path, logger: logging.Logger) -> str:
        api_key = self.config.llm_key or self.settings.llm_api_key
        if not api_key:
            logger.warning("OPENAI_API_KEY não definido; ASR será pulado.")
            return ""
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning("SDK OpenAI indisponível: %s", exc)
            return ""
        client = OpenAI(api_key=api_key)
        try:
            if hasattr(client, "audio") and hasattr(client.audio, "transcriptions"):
                create = getattr(client.audio.transcriptions, "create", None)
                if create:
                    with path.open("rb") as stream:
                        response = create(model=OPENAI_WHISPER_MODEL, file=stream)
                    text = getattr(response, "text", "")
                    return str(text).strip()
            if hasattr(client, "Audio") and hasattr(client.Audio, "transcribe"):
                with path.open("rb") as stream:
                    response = client.Audio.transcribe(OPENAI_WHISPER_MODEL, stream)
                return str(getattr(response, "text", "")).strip()
        except Exception as exc:  # pragma: no cover
            logger.warning("Transcrição via OpenAI falhou: %s", exc)
        return ""

    def _persist_outputs(
        self,
        run_id: str,
        channels: list[dict],
        total_videos: int,
        timestamp: datetime,
    ) -> tuple[Optional[Path], Optional[Path]]:
        metadata = {
            "executed_at": timestamp.isoformat(),
            "mode": self.config.mode,
            "total_channels": len(channels),
            "total_videos": total_videos,
            "params": {
                "days": self.config.days,
                "max_videos": self.config.max_videos,
                "mode": self.config.mode,
                "no_llm": self.config.no_llm,
                "asr_provider": self.config.asr_provider,
                "format": self.config.report_format,
            },
            "channels": channels,
        }
        json_path = self.resultados_dir / f"{self.config.prefix}_{run_id}.json"
        json_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path = self._build_report(run_id, metadata)
        return json_path, report_path

    def _build_report(self, run_id: str, metadata: dict) -> Optional[Path]:
        formato = self.config.report_format.lower()
        texto = self._report_text(metadata)
        if formato == "txt":
            path = self.resultados_dir / f"{self.config.prefix}_{run_id}.txt"
            path.write_text(texto, encoding="utf-8")
            return path
        if formato == "html":
            path = self.resultados_dir / f"{self.config.prefix}_{run_id}.html"
            html_content = f"<html><body><pre>{html.escape(texto)}</pre></body></html>"
            path.write_text(html_content, encoding="utf-8")
            return path
        if formato == "pdf":
            path = self.resultados_dir / f"{self.config.prefix}_{run_id}.pdf"
            self._save_pdf(texto, path)
            return path
        if formato == "json":
            return None
        # fallback para txt
        path = self.resultados_dir / f"{self.config.prefix}_{run_id}.txt"
        path.write_text(texto, encoding="utf-8")
        return path

    def _report_text(self, metadata: dict) -> str:
        lines = []
        lines.append("=======================================================================")
        lines.append("📊 RESUMO DA EXTRAÇÃO")
        lines.append("=======================================================================\n")
        lines.append(f"Canais processados: {metadata['total_channels']}")
        lines.append(f"Total de vídeos extraídos: {metadata['total_videos']}")
        lines.append(f"Modo: {metadata['params']['mode']}")
        lines.append(
            f"Parâmetros: dias={metadata['params']['days']}, max_videos={metadata['params']['max_videos']},"
            f" formato={metadata['params']['format']}"
        )
        lines.append("")
        for channel in metadata.get("channels", []):
            lines.append(f"✅ {channel.get('name')} ({channel.get('channel_id')})")
            videos = channel.get("videos", [])
            lines.append(f"    Vídeos extraídos: {len(videos)}")
            for video in videos:
                lines.append(
                    f"    - {video.get('title')} — {video.get('duration') or 'N/A'} — {video.get('url')}"
                )
                summary = video.get("summary")
                if summary:
                    lines.append(f"      Resumo: {summary.get('resumo_uma_frase', '')}")
        lines.append("\n=======================================================================")
        lines.append("✨ Extração concluída!")
        return "\n".join(lines)

    def _save_pdf(self, texto: str, path: Path) -> None:
        pdf = FPDF()
        pdf.add_page()
        try:
            pdf.set_font("Helvetica", size=12)
        except Exception:  # pragma: no cover - fallback for environments without Helvetica
            pdf.set_font("Arial", size=12)
        max_width = pdf.w - pdf.l_margin - pdf.r_margin
        for line in texto.splitlines():
            if not line.strip():
                pdf.ln(8)
                continue
            chunk = line
            while chunk:
                span = len(chunk)
                while span > 0 and pdf.get_string_width(chunk[:span]) > max_width:
                    span -= 1
                pdf.cell(0, 6, txt=chunk[:span], ln=1)
                chunk = chunk[span:]
        pdf.output(str(path))
