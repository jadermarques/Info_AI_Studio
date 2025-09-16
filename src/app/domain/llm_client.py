"""LLM client abstraction used to summarise video transcripts."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from typing import Optional

LOGGER = logging.getLogger(__name__)

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency for tests
    OpenAI = None  # type: ignore


@dataclass(slots=True)
class LLMResult:
    """Structured response from a summarisation request."""

    resumo_uma_frase: str
    resumo: str
    assunto_principal: str
    palavras_chave: list[str]
    resumo_em_topicos: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    cost: float


class LLMClient:
    """Wrapper around supported LLM providers."""

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str],
        token_limit: int,
    ) -> None:
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or ""
        self.token_limit = token_limit
        self._client = None
        if self.provider == "openai" and self.api_key and OpenAI is not None:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - depends on runtime
                LOGGER.warning("Falha ao inicializar cliente OpenAI: %s", exc)
                self._client = None
        elif self.api_key:
            LOGGER.warning("Provedor LLM '%s' não suportado; análises serão desativadas.", provider)

    @property
    def active(self) -> bool:
        """Return True when the provider can perform requests."""

        return self._client is not None

    def summarise(
        self,
        title: str,
        transcript: str,
        channel: str,
        max_palavras: int,
    ) -> LLMResult:
        """Generate a structured summary for a transcript."""

        transcript_clean = transcript.strip()
        if not transcript_clean:
            LOGGER.info("[LLM] Transcrição vazia — pulando análise para %s", title)
            return LLMResult("", "", "", [], "", 0, 0, self.model, 0.0)
        if not self.active:
            LOGGER.info("[LLM] Cliente LLM ausente — usando resumo heurístico.")
            return self._heuristic_summary(title, transcript_clean, max_palavras)
        prompt = (
            "Você é um analista. Resuma a transcrição de um vídeo do YouTube.\n"
            f"Título: {title}\n"
            f"Canal: {channel}\n"
            f"Transcrição: {transcript_clean[: min(len(transcript_clean), 8000)]}\n"
            "Responda em JSON válido com as chaves: resumo_do_video_uma_frase,"
            " resumo_do_video, assunto_principal, palavras_chave (lista) e resumo_em_topicos (Markdown)."
            f" Limite o campo resumo_do_video a {max_palavras} palavras."
        )
        try:
            response = None
            client = self._client
            if client is None:
                raise RuntimeError("LLM client not available")
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self._max_output_tokens(),
                )
                content = response.choices[0].message.content if response.choices else ""
                usage = getattr(response, "usage", None)
                prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            else:  # pragma: no cover - legacy clients
                create = getattr(getattr(client, "ChatCompletion", None), "create", None)
                if not create:
                    raise RuntimeError("OpenAI client incompatível")
                response = create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self._max_output_tokens(),
                )
                content = response["choices"][0]["message"]["content"] if response else ""
                usage = response.get("usage", {}) if isinstance(response, dict) else {}
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
            if not content:
                LOGGER.warning("[LLM] Resposta vazia do modelo para %s", title)
                return LLMResult("", "", "", [], "", 0, 0, self.model, 0.0)
            data = json.loads(content)
            return LLMResult(
                resumo_uma_frase=str(data.get("resumo_do_video_uma_frase", "")),
                resumo=str(data.get("resumo_do_video", "")),
                assunto_principal=str(data.get("assunto_principal", "")),
                palavras_chave=list(data.get("palavras_chave", [])),
                resumo_em_topicos=str(data.get("resumo_em_topicos", "")),
                prompt_tokens=int(prompt_tokens or 0),
                completion_tokens=int(completion_tokens or 0),
                model=self.model,
                cost=0.0,
            )
        except Exception as exc:  # pragma: no cover - depends on API
            LOGGER.warning("[LLM] Erro durante chamada ao modelo: %s", exc)
            return self._heuristic_summary(title, transcript_clean, max_palavras)

    def _heuristic_summary(
        self, title: str, transcript: str, max_palavras: int
    ) -> LLMResult:
        """Generate a lightweight summary when no LLM is available."""

        words = transcript.split()
        resumo_words = words[: max(1, min(len(words), max_palavras))]
        resumo = " ".join(resumo_words)
        resumo_uma_frase = resumo.split(".")[0][:280] if resumo else ""
        keywords = sorted({w.strip(".,;:!?\"'").lower() for w in words[:200] if len(w) > 4})
        topicos = "\n".join(f"- {token}" for token in keywords[:8])
        return LLMResult(
            resumo_uma_frase=resumo_uma_frase,
            resumo=resumo,
            assunto_principal=title[:120],
            palavras_chave=list(keywords[:12]),
            resumo_em_topicos=topicos,
            prompt_tokens=0,
            completion_tokens=0,
            model=self.model,
            cost=0.0,
        )

    def _max_output_tokens(self) -> int:
        """Calculate a conservative output token limit."""

        # heurística simples: 4 tokens por palavra + margem
        return max(256, math.ceil(self.token_limit * 0.25))