 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/src/app/domain/youtube/service.py b/src/app/domain/youtube/service.py
index 61bee605b0a37d9058097893ad4e687c4136a3f5..74f798c04e0dca47fd42c14bc59f609b289c85be 100644
--- a/src/app/domain/youtube/service.py
+++ b/src/app/domain/youtube/service.py
@@ -132,93 +132,98 @@ class YouTubeExecutionService:
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
+                    analysis_source = "modo_simples"
                     summary: Optional[LLMResult] = None
                     if self.config.mode.lower() == "full":
-                        transcript = self._obter_transcricao(video_id, extractor, logger)
+                        transcript, analysis_source = self._obter_transcricao(
+                            video_id, extractor, logger
+                        )
                         if transcript and not self.config.no_llm:
                             summary = llm_client.summarise(
                                 title=video.get("title", ""),
                                 transcript=transcript,
                                 channel=info.get("name") or channel,
                                 max_palavras=self.config.resumo_max_palavras,
                                 translate_mode=self.config.translate_results,
                             )
                         elif self.config.no_llm:
                             logger.info(
                                 "[LLM] Execução com --no-llm habilitado; resumos serão pulados."
                             )
+                    self._log_analysis_origin(logger, video_id, analysis_source)
                     prompt_tokens = summary.prompt_tokens if summary else 0
                     completion_tokens = summary.completion_tokens if summary else 0
                     prompt_tokens_channel += prompt_tokens
                     completion_tokens_channel += completion_tokens
                     token_details.append(
                         {
                             "canal": info.get("name") or channel,
                             "video": video.get("title", ""),
                             "video_id": video_id,
                             "modelo": summary.model if summary else self.config.llm_model,
                             "tokens_entrada": prompt_tokens,
                             "tokens_saida": completion_tokens,
                             "tokens_totais": prompt_tokens + completion_tokens,
                             "custo_estimado": (summary.cost if summary else 0.0),
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
+                            "analysis_source": analysis_source,
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
diff --git a/src/app/domain/youtube/service.py b/src/app/domain/youtube/service.py
index 61bee605b0a37d9058097893ad4e687c4136a3f5..74f798c04e0dca47fd42c14bc59f609b289c85be 100644
--- a/src/app/domain/youtube/service.py
+++ b/src/app/domain/youtube/service.py
@@ -309,70 +314,108 @@ class YouTubeExecutionService:
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
 
+    @staticmethod
+    def _log_analysis_origin(logger: logging.Logger, video_id: str, source: str) -> None:
+        if source == "transcricao_youtube":
+            logger.info(
+                "Vídeo %s analisado com a transcrição disponibilizada pelo YouTube.",
+                video_id,
+            )
+        elif source == "sem_transcricao":
+            logger.info(
+                "Vídeo %s sem transcrição disponível; resumo não será gerado.",
+                video_id,
+            )
+        elif source == "modo_simples":
+            logger.info(
+                "Vídeo %s executado no modo simple (transcrição não aplicada).",
+                video_id,
+            )
+        elif source.startswith("asr_"):
+            logger.info(
+                "Vídeo %s analisado via ASR (áudio baixado) [%s].",
+                video_id,
+                source,
+            )
+        else:
+            logger.info("Vídeo %s analisado pelo método %s.", video_id, source)
+
     def _obter_transcricao(
         self,
         video_id: str,
         extractor: YouTubeExtractor,
         logger: logging.Logger,
-    ) -> str:
+    ) -> tuple[str, str]:
         text = extractor.fetch_transcript_text(video_id)
         if text:
-            return text
+            logger.info("Transcrição nativa encontrada para %s", video_id)
+            return text, "transcricao_youtube"
         if not self.config.asr_enabled:
             logger.info("[ASR desativado] Sem transcrição YouTube para %s", video_id)
-            return ""
+            return "", "sem_transcricao"
         logger.info("[ASR ativado] Transcrição não encontrada; iniciando fallback para %s", video_id)
         with tempfile.TemporaryDirectory() as tmp_dir:
             audio_path = self._download_audio(video_id, Path(tmp_dir), logger)
             if not audio_path:
-                return ""
+                logger.info("Não foi possível baixar áudio para %s; transcrição indisponível.", video_id)
+                return "", "sem_transcricao"
             if self.config.asr_provider == "openai":
-                return self._asr_openai(audio_path, logger)
-            return self._asr_faster_whisper(audio_path, logger)
+                texto_asr = self._asr_openai(audio_path, logger)
+                if texto_asr:
+                    logger.info("Transcrição obtida via ASR OpenAI para %s", video_id)
+                    return texto_asr, "asr_openai"
+                logger.info("ASR OpenAI não retornou conteúdo para %s", video_id)
+                return "", "sem_transcricao"
+            texto_asr = self._asr_faster_whisper(audio_path, logger)
+            if texto_asr:
+                logger.info("Transcrição obtida via ASR faster-whisper para %s", video_id)
+                return texto_asr, "asr_faster_whisper"
+            logger.info("ASR faster-whisper não retornou conteúdo para %s", video_id)
+            return "", "sem_transcricao"
 
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
 
EOF
)