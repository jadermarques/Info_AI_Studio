diff --git a/scripts/create_project.sh b/scripts/create_project.sh
index e162fa24d542dbc2210a01dbf2f7a26a5bc6cb31..35ebb04cc2871fc14c4f3cb6c467347ca5a63d3d 100755
--- a/scripts/create_project.sh
+++ b/scripts/create_project.sh
@@ -1558,51 +1558,65 @@ class YouTubeExtractor:
                     TranslationLanguageNotAvailable,
                 )
             except Exception:
                 RequestBlocked = IpBlocked = YouTubeRequestFailed = (
                     CouldNotRetrieveTranscript
                 ) = TranslationLanguageNotAvailable = Exception
         except Exception as e:
             logger.info(f"Transcrição: biblioteca youtube_transcript_api indisponível: {e}")
             return ""
 
         blocked_errors = (
             RequestBlocked,
             IpBlocked,
             YouTubeRequestFailed,
             CouldNotRetrieveTranscript,
         )
 
         def _short_err(e: Exception) -> str:
             """Retorna uma versão resumida, porém sempre preenchida, do erro."""
             msg = str(e).strip()
             if not msg:
                 msg = repr(e)
             return msg.splitlines()[0].strip()
 
         def _join(tr_list):
-            return " ".join([t.get("text", "") for t in tr_list if t.get("text")])
+            parts = []
+            for item in tr_list:
+                text = getattr(item, "text", None)
+                if text:
+                    parts.append(text)
+                    continue
+                getter = getattr(item, "get", None)
+                if callable(getter):
+                    try:
+                        text = getter("text", None)
+                    except Exception:
+                        text = None
+                if text:
+                    parts.append(text)
+            return " ".join(parts)
 
         # 1) listar transcript objects (compatibilidade com versões novas/antigas)
         try:
             tl = None
             for attr in ("list_transcripts", "list"):
                 fn = getattr(YouTubeTranscriptApi, attr, None)
                 if not callable(fn):
                     continue
                 try:
                     tl = fn(video_id)
                     break
                 except TypeError:
                     # método de instância
                     api = YouTubeTranscriptApi()
                     inst_fn = getattr(api, attr, None)
                     if callable(inst_fn):
                         tl = inst_fn(video_id)
                         break
             if tl is None:
                 raise AttributeError("YouTubeTranscriptApi.list(_transcripts) ausente")
         except blocked_errors as e:
             logger.info(
                 f"Transcrição: acesso bloqueado ao listar para {video_id}: {_short_err(e)}"
             )
             return self._fetch_transcript_ytdlp(video_id, preferred_langs)
