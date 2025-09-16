# -*- coding: utf-8 -*-
"""
YouTube Extractor (plus)
- Extrai vídeos da aba /videos (ignora Shorts/Live/Upcoming)
- Filtra por janela de dias (max_age_days)
- Lê /about para dados do canal
- Obtém metadados do vídeo (duração/data) pela página do vídeo
- Obtém transcrição com youtube_transcript_api (preferindo transcrições nativas; tradução se necessário)
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("youtube_extractor")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class YouTubeExtractor:
    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: int = 25,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.user_agent = user_agent

    # --------------------- Infra ---------------------
    def get_http_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
        }

    def _make_request(self, url: str) -> Optional[requests.Response]:
        try:
            return self.session.get(url, headers=self.get_http_headers(), timeout=self.timeout)
        except Exception as e:
            logger.warning(f"Falha ao requisitar {url}: {e}")
            return None

    def _normalize_text_basic(self, s: str) -> str:
        if not s:
            return ""
        import unicodedata
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return s.lower().strip()

    def _normalize_channel_videos_url(self, channel_id: str) -> str:
        if channel_id.startswith("UC"):
            return f"https://www.youtube.com/channel/{channel_id}/videos"
        if channel_id.startswith("@"):
            return f"https://www.youtube.com/{channel_id}/videos"
        return f"https://www.youtube.com/@{channel_id}/videos"

    def _normalize_channel_about_url(self, channel_id: str) -> str:
        if channel_id.startswith("UC"):
            return f"https://www.youtube.com/channel/{channel_id}/about"
        if channel_id.startswith("@"):
            return f"https://www.youtube.com/{channel_id}/about"
        return f"https://www.youtube.com/@{channel_id}/about"

    # --------------------- Tempo relativo ---------------------
    def _parse_relative_time(self, text: str) -> Optional[datetime]:
        if not text:
            return None
        t = text.strip().lower()
        if any(k in t for k in ["live now", "ao vivo", "transmitindo agora", "upcoming", "programado"]):
            return None
        now = datetime.utcnow()
        t = (
            t.replace("atrás", "")
            .replace("ago", "")
            .replace("há", "")
            .replace("streamed", "")
            .replace("transmitido", "")
            .strip()
        )
        pats = [
            (r"(\d+)\s*min", "minutes"),
            (r"(\d+)\s*minute", "minutes"),
            (r"(\d+)\s*hora", "hours"),
            (r"(\d+)\s*hour", "hours"),
            (r"(\d+)\s*dia", "days"),
            (r"(\d+)\s*day", "days"),
            (r"(\d+)\s*semana", "weeks"),
            (r"(\d+)\s*week", "weeks"),
            (r"(\d+)\s*m[eê]s", "months"),
            (r"(\d+)\s*month", "months"),
            (r"(\d+)\s*ano", "years"),
            (r"(\d+)\s*year", "years"),
        ]
        for pat, unit in pats:
            m = re.search(pat + r"s?", t)
            if m:
                n = int(m.group(1))
                if unit == "minutes":
                    return now - timedelta(minutes=n)
                if unit == "hours":
                    return now - timedelta(hours=n)
                if unit == "days":
                    return now - timedelta(days=n)
                if unit == "weeks":
                    return now - timedelta(weeks=n)
                if unit == "months":
                    return now - timedelta(days=30 * n)
                if unit == "years":
                    return now - timedelta(days=365 * n)
        return None

    # --------------------- Extração de vídeos ---------------------
    def extract_recent_videos(
        self,
        channel_id: str,
        max_age_days: Optional[int] = None,
        videos_tab_only: bool = True,
        max_videos: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        logger.info(
            "Extraindo vídeos do canal {} (max_age_days={}, videos_tab_only={}, max_videos={})".format(
                channel_id, max_age_days, videos_tab_only, max_videos
            )
        )
        return self._extract_from_videos_tab(
            channel_id, max_age_days=max_age_days, max_videos=max_videos
        )

    def _extract_from_videos_tab(
        self, channel_id: str, max_age_days: Optional[int], max_videos: Optional[int] = None
    ) -> List[Dict[str, str]]:
        url = self._normalize_channel_videos_url(channel_id)
        resp = self._make_request(url)
        if not resp or resp.status_code != 200:
            logger.warning(f"Falha ao acessar {url}")
            return []
        html = resp.text

        # Localiza ytInitialData
        initial_data = None
        for ptn in [
            r"var ytInitialData = (\{.*?\});",
            r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayer',
            r'ytInitialData"\s*:\s*(\{.*?\})\s*[,}]',
        ]:
            m = re.search(ptn, html, re.S)
            if m:
                try:
                    initial_data = json.loads(m.group(1))
                    break
                except Exception:
                    pass
        if not initial_data:
            logger.warning("Não foi possível localizar ytInitialData na aba /videos")
            return []

        # Conteúdo da aba "Vídeos"
        contents = []
        continuation_token = None
        rgr = {}
        try:
            tabs = initial_data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
            for tab in tabs:
                tr = tab.get("tabRenderer", {})
                raw_title = tr.get("title") or ""
                title_norm = self._normalize_text_basic(raw_title)
                selected = tr.get("selected") is True
                if "videos" in title_norm or selected:
                    rgr = tr.get("content", {}).get("richGridRenderer", {})
                    contents = rgr.get("contents", [])
                    try:
                        continuation_token = (
                            rgr["continuations"][0]["nextContinuationData"]["continuation"]
                        )
                    except Exception:
                        continuation_token = None
                    break
        except Exception:
            pass

        videos: List[Dict[str, str]] = []
        shelves_skipped = 0
        live_count = 0
        upcoming_count = 0
        nodate_count = 0
        older_count = 0
        parsed_count = 0

        def push_video(vr: dict) -> bool:
            nonlocal live_count, upcoming_count, nodate_count, older_count
            vid = vr.get("videoId")
            if not vid:
                return True

            badges = vr.get("badges") or []
            is_live = any("LIVE" in (b.get("metadataBadgeRenderer", {}).get("label") or "").upper() for b in badges)
            upcoming = vr.get("upcomingEventData") is not None
            if is_live or upcoming:
                if is_live:
                    live_count += 1
                if upcoming:
                    upcoming_count += 1
                return True

            title = ""
            try:
                title = vr["title"]["runs"][0]["text"]
            except Exception:
                pass

            rel = ""
            try:
                rel = vr.get("publishedTimeText", {}).get("simpleText", "") or ""
            except Exception:
                pass

            published_dt = self._parse_relative_time(rel)

            if max_age_days is not None:
                if published_dt is None:
                    nodate_count += 1
                    return True
                age_days = (datetime.utcnow() - published_dt).days
                if age_days > max_age_days:
                    older_count += 1
                    return False

            videos.append(
                {
                    "id": vid,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "published": published_dt.isoformat() if published_dt else "",
                    "published_relative": rel,
                }
            )

            if max_videos is not None and len(videos) >= max_videos:
                return False

            return True

        stop = False
        for item in contents:
            if "reelShelfRenderer" in item or "richSectionRenderer" in item:
                shelves_skipped += 1
                continue
            content = item.get("richItemRenderer", {}).get("content") or item
            if "videoRenderer" in content:
                parsed_count += 1
                if not push_video(content["videoRenderer"]):
                    stop = True
                    break
            elif "gridVideoRenderer" in content:
                parsed_count += 1
                if not push_video(content["gridVideoRenderer"]):
                    stop = True
                    break

        # Processa continuations
        if not stop and continuation_token:
            api_key = None
            context = {}
            try:
                api_key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', html).group(1)
                context = json.loads(
                    re.search(r'"INNERTUBE_CONTEXT":(\{.*?\})', html, re.S).group(1)
                )
            except Exception:
                api_key = None
                context = {}

            headers = self.get_http_headers()
            headers["Content-Type"] = "application/json"

            token = continuation_token
            while token and (max_videos is None or len(videos) < max_videos):
                try:
                    browse_url = f"https://www.youtube.com/youtubei/v1/browse?key={api_key}"
                    payload = {"continuation": token, "context": context}
                    resp = self.session.post(
                        browse_url, json=payload, headers=headers, timeout=self.timeout
                    )
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                except Exception:
                    break

                items = (
                    data.get("onResponseReceivedActions", [{}])[0]
                    .get("appendContinuationItemsAction", {})
                    .get("continuationItems", [])
                )
                token = None
                for item in items:
                    if "continuationItemRenderer" in item:
                        try:
                            token = (
                                item["continuationItemRenderer"]["continuationEndpoint"][
                                    "continuationCommand"
                                ]["token"]
                            )
                        except Exception:
                            token = None
                        continue
                    if "reelShelfRenderer" in item or "richSectionRenderer" in item:
                        shelves_skipped += 1
                        continue
                    content = item.get("richItemRenderer", {}).get("content") or item
                    if "videoRenderer" in content:
                        parsed_count += 1
                        if not push_video(content["videoRenderer"]):
                            stop = True
                            break
                    elif "gridVideoRenderer" in content:
                        parsed_count += 1
                        if not push_video(content["gridVideoRenderer"]):
                            stop = True
                            break
                if stop or not token:
                    break

        logger.info(
            "Aba /videos: analisados={parsed}, válidos={validos}, ignorados: live={live}, upcoming={up}, "
            "sem_data={nd}, antigos={old}, shelves={shelves}".format(
                parsed=parsed_count,
                validos=len(videos),
                live=live_count,
                up=upcoming_count,
                nd=nodate_count,
                old=older_count,
                shelves=shelves_skipped,
            )
        )
        logger.info(
            "Aba /videos: {} vídeos válidos{}".format(
                len(videos), f" (≤ {max_age_days} dias)" if max_age_days is not None else ""
            )
        )
        return videos

    # --------------------- Canal /about ---------------------
    def extract_channel_info(self, channel_id: str) -> Dict[str, str]:
        url = self._normalize_channel_about_url(channel_id)
        resp = self._make_request(url)
        if not resp or resp.status_code != 200:
            return {"status": "error", "message": f"Falha ao acessar {url}"}

        html = resp.text
        initial_data = None
        for ptn in [
            r"var ytInitialData = (\{.*?\});",
            r'ytInitialData"\s*:\s*(\{.*?\})\s*,\s*"ytInitialPlayer',
            r'ytInitialData"\s*:\s*(\{.*?\})\s*[,}]',
        ]:
            m = re.search(ptn, html, re.S)
            if m:
                try:
                    initial_data = json.loads(m.group(1))
                    break
                except Exception:
                    pass

        name = channel_id
        description = ""
        subs = ""
        video_count = ""

        try:
            header = initial_data["header"]["c4TabbedHeaderRenderer"]
            name = header.get("title", name)
            subs = (header.get("subscriberCountText", {}).get("simpleText") or subs).strip()
            about_tabs = initial_data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"]
            for tab in about_tabs:
                tr = tab.get("tabRenderer", {})
                title_norm = self._normalize_text_basic(tr.get("title") or "")
                if "about" in title_norm or "sobre" in title_norm:
                    sec = tr.get("content", {}).get("sectionListRenderer", {}).get("contents", [])
                    if sec:
                        text = sec[0].get("itemSectionRenderer", {}).get("contents", [])
                        if text:
                            desc = text[0].get("channelAboutFullMetadataRenderer", {}).get("description", {})
                            description = (desc.get("simpleText") or description).strip()
                    break
        except Exception:
            pass

        try:
            video_count = str(initial_data["metadata"]["channelMetadataRenderer"].get("videoCount", ""))
        except Exception:
            pass

        return {
            "status": "success",
            "name": name or channel_id,
            "subscriber_count": subs,
            "description": description or "",
            "video_count": video_count,
        }

    # --------------------- Lote ---------------------
    def extract_batch_channels(
        self,
        channel_ids: List[str],
        include_videos: bool = True,
        max_age_days: Optional[int] = None,
        videos_tab_only: bool = True,
        max_videos: Optional[int] = None,
    ) -> Dict[str, Dict]:
        results: Dict[str, Dict] = {"channels": {}}
        start = time.time()
        for i, cid in enumerate(channel_ids, 1):
            logger.info(f"[{i}/{len(channel_ids)}] Canal: {cid}")
            info = self.extract_channel_info(cid)
            results["channels"][cid] = info
            if include_videos and info.get("status") == "success":
                vids = self.extract_recent_videos(
                    cid,
                    max_age_days=max_age_days,
                    videos_tab_only=videos_tab_only,
                    max_videos=max_videos,
                )
                info["recent_videos"] = vids
                info["video_count_extracted"] = len(vids)

        results["took_seconds"] = round(time.time() - start, 3)
        results["params"] = {
            "include_videos": include_videos,
            "max_age_days": max_age_days,
            "videos_tab_only": videos_tab_only,
            "max_videos": max_videos,
        }
        return results

    # --------------------- Metadados e Transcrição ---------------------
    def _parse_iso8601_duration(self, iso: str) -> int:
        try:
            m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", iso or "")
            if not m:
                return 0
            h = int(m.group(1) or 0)
            m_ = int(m.group(2) or 0)
            s = int(m.group(3) or 0)
            return h * 3600 + m_ * 60 + s
        except Exception:
            return 0

    def _format_hhmmss(self, seconds: int) -> str:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def fetch_video_details(self, video_id: str) -> Dict[str, str]:
        """Duração (segundos, hh:mm:ss) e data de publicação pela página do vídeo."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        resp = self._make_request(url)
        if not resp or resp.status_code != 200:
            return {"duration_seconds": 0, "duration_hhmmss": "", "date_published": "", "url": url}

        html = resp.text
        duration_seconds = 0
        date_published = ""

        # JSON-LD
        try:
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.S | re.I):
                data = json.loads(m.group(1))
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "VideoObject":
                            iso = item.get("duration") or ""
                            duration_seconds = self._parse_iso8601_duration(iso) or duration_seconds
                            date_published = item.get("uploadDate") or item.get("datePublished") or date_published
                elif isinstance(data, dict) and data.get("@type") == "VideoObject":
                    iso = data.get("duration") or ""
                    duration_seconds = self._parse_iso8601_duration(iso) or duration_seconds
                    date_published = data.get("uploadDate") or data.get("datePublished") or date_published
        except Exception:
            pass

        # ytInitialPlayerResponse
        if duration_seconds == 0 or not date_published:
            try:
                m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.*?\})\s*;", html, re.S)
                if m:
                    p = json.loads(m.group(1))
                    ls = p.get("videoDetails", {}).get("lengthSeconds")
                    if ls and str(ls).isdigit():
                        duration_seconds = int(ls)
                    micro = p.get("microformat", {}).get("playerMicroformatRenderer", {})
                    date_published = micro.get("publishDate") or micro.get("uploadDate") or date_published
            except Exception:
                pass

        return {
            "duration_seconds": duration_seconds,
            "duration_hhmmss": self._format_hhmmss(duration_seconds) if duration_seconds else "",
            "date_published": date_published or "",
            "url": url,
        }

    def _fetch_transcript_ytdlp(self, video_id: str, preferred_langs=None) -> str:
        """Fallback de transcrição via yt-dlp, usando legendas do YouTube."""
        try:
            import yt_dlp
        except Exception:
            return ""
        langs = preferred_langs or ["pt", "pt-BR", "pt-PT", "en"]
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": langs,
            "subtitlesformat": "vtt",
        }
        try:
            import os
            if os.path.exists("cookies.txt"):
                ydl_opts["cookiefile"] = "cookies.txt"
                logger.info("yt-dlp usando cookies de cookies.txt")
        except Exception:
            pass
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            subs = info.get("subtitles") or {}
            auto = info.get("automatic_captions") or {}

            def _grab(src):
                for lang in langs:
                    tracks = src.get(lang)
                    if not tracks:
                        continue
                    link = tracks[0].get("url")
                    if not link:
                        continue
                    try:
                        resp = requests.get(
                            link, headers=self.get_http_headers(), timeout=self.timeout
                        )
                        if resp.status_code == 200:
                            return self._vtt_to_text(resp.text)
                    except Exception:
                        continue
                return ""

            text = _grab(subs)
            if text:
                return text
            return _grab(auto)
        except Exception as e:
            logger.info(f"Transcrição: yt-dlp falhou para {video_id}: {e}")
        return ""

    def _vtt_to_text(self, data: str) -> str:
        lines = []
        for line in data.splitlines():
            line = line.strip()
            if (
                not line
                or line.startswith("WEBVTT")
                or line.startswith("#")
                or "-->" in line
                or line.isdigit()
            ):
                continue
            lines.append(line)
        return " ".join(lines)

    def fetch_transcript_text(self, video_id: str, preferred_langs=None) -> str:
        """Transcrição concatenada via youtube_transcript_api (quando disponível).
        Preferência: manual > gerada; tenta idiomas preferidos e, se necessário, tradução.
        Importa apenas YouTubeTranscriptApi para ser compatível com várias versões.
        """
        if preferred_langs is None:
            preferred_langs = ["pt", "pt-BR", "pt-PT", "en"]

        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            try:
                from youtube_transcript_api._errors import (
                    RequestBlocked,
                    IpBlocked,
                    YouTubeRequestFailed,
                    CouldNotRetrieveTranscript,
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
            return " ".join([t.get("text", "") for t in tr_list if t.get("text")])

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
        except Exception as e:
            logger.info(
                f"Transcrição: falha ao listar para {video_id}: {_short_err(e)}"
            )
            return self._fetch_transcript_ytdlp(video_id, preferred_langs)

        # lista concreta para múltiplas passagens
        all_transcripts = list(tl)
        if not all_transcripts:
            logger.info(f"Transcrição: nenhuma disponível para {video_id}")
            return self._fetch_transcript_ytdlp(video_id, preferred_langs)

        disp = [f"{t.language_code}{'(auto)' if t.is_generated else ''}" for t in all_transcripts]
        logger.info(f"Transcrição: disponíveis {disp} para {video_id}")

        def _try_fetch(tr) -> Tuple[str, bool]:
            try:
                text = _join(tr.fetch())
                if text.strip():
                    logger.info(
                        f"Transcrição encontrada ({len(text)} chars, {tr.language_code}) para {video_id}"
                    )
                    return text, False
            except blocked_errors as e:
                logger.info(
                    f"Transcrição: acesso bloqueado ou indisponível para {video_id}: {_short_err(e)}"
                )
                text = self._fetch_transcript_ytdlp(video_id, preferred_langs)
                if text:
                    return text, False
                return "", True
            except Exception as e:
                logger.info(
                    f"Transcrição: falha ao obter {tr.language_code}{'(auto)' if getattr(tr, 'is_generated', False) else ''} para {video_id}: {_short_err(e)}"
                )
            return "", False

        # 2) buscar transcript manual ou gerada pelos idiomas preferidos
        for lang in preferred_langs + ["pt-BR", "pt-PT", "en"]:
            try:
                tr = tl.find_manually_created_transcript([lang])
                text, blocked = _try_fetch(tr)
                if text:
                    return text
                if blocked:
                    return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except Exception:
                pass
            try:
                tr = tl.find_generated_transcript([lang])
                text, blocked = _try_fetch(tr)
                if text:
                    return text
                if blocked:
                    return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except Exception:
                pass

        # 3) traduzir a primeira disponível para pt
        for tr in all_transcripts:
            try:
                tr_pt = tr.translate("pt")
                text, blocked = _try_fetch(tr_pt)
                if text:
                    return text
                if blocked:
                    return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except TranslationLanguageNotAvailable:
                logger.info(
                    f"Transcrição: tradução pt indisponível para {tr.language_code} em {video_id}"
                )
            except blocked_errors as e:
                logger.info(
                    f"Transcrição: acesso bloqueado ao traduzir {tr.language_code} para {video_id}: {_short_err(e)}"
                )
                return self._fetch_transcript_ytdlp(video_id, preferred_langs)
            except Exception as e:
                logger.info(
                    f"Transcrição: falha ao traduzir {tr.language_code} para {video_id}: {_short_err(e)}"
                )

        # 4) fallback: primeira transcript "como está"
        for tr in all_transcripts:
            text, blocked = _try_fetch(tr)
            if text:
                return text
            if blocked:
                return self._fetch_transcript_ytdlp(video_id, preferred_langs)

        logger.info(f"Transcrição: não encontrada para {video_id}")
        return self._fetch_transcript_ytdlp(video_id, preferred_langs)
