"""LLM client abstraction used to summarise video transcripts."""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Optional

LOGGER = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)


def _safe_int(value: Any) -> int:
    """Convert values that might be None/str/float into integers safely."""

    if value in (None, ""):
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        text = str(value).strip()
        if not text:
            return 0
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def _coerce_to_text(value: Any) -> str:
    """Extract textual content from heterogeneous OpenAI SDK objects."""

    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple, set)):
        return "".join(_coerce_to_text(item) for item in value)
    if isinstance(value, dict):
        for key in ("text", "content", "value", "message"):
            if key in value:
                text = _coerce_to_text(value[key])
                if text:
                    return text
        # fallback: concatenate string values if present
        parts = [str(item) for item in value.values() if isinstance(item, str)]
        return " ".join(parts)
    for attr in ("text", "value", "content"):
        if hasattr(value, attr):
            attr_value = getattr(value, attr)
            if attr_value is not value:
                text = _coerce_to_text(attr_value)
                if text:
                    return text
    return str(value)


def _extract_usage_numbers(usage: Any) -> tuple[int, int]:
    """Retrieve prompt and completion tokens from different usage schemas."""

    if usage is None:
        return 0, 0

    def _read(keys: tuple[str, ...]) -> int:
        for key in keys:
            if isinstance(usage, dict):
                value = usage.get(key)
            else:
                value = getattr(usage, key, None)
            if value is not None:
                return _safe_int(value)
        return 0

    prompt_tokens = _read(("prompt_tokens", "input_tokens"))
    completion_tokens = _read(("completion_tokens", "output_tokens"))
    total_tokens = _read(("total_tokens",))

    if not completion_tokens and total_tokens and prompt_tokens:
        completion_tokens = max(0, total_tokens - prompt_tokens)
    elif not completion_tokens and total_tokens:
        completion_tokens = total_tokens
    if not prompt_tokens and total_tokens and completion_tokens:
        prompt_tokens = max(0, total_tokens - completion_tokens)

    return prompt_tokens, completion_tokens


def _normalize_json_payload(payload: str) -> str:
    """Strip markdown fences and unrelated prefixes from JSON blobs."""

    text = payload.strip()
    if not text:
        return ""
    match = _JSON_BLOCK_RE.match(text)
    if match:
        text = match.group(1).strip()
    if text.startswith("{") or text.startswith("["):
        return text
    first_brace = text.find("{")
    first_bracket = text.find("[")
    indices = [idx for idx in (first_brace, first_bracket) if idx >= 0]
    if indices:
        idx = min(indices)
        candidate = text[idx:].strip()
        if candidate:
            text = candidate
    return text


def _preview(text: str, limit: int = 180) -> str:
    """Return a compact single-line preview for logging."""

    normalized = text.replace("\n", " ")
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "…"


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
            LOGGER.warning(
                "Provedor LLM '%s' não suportado; análises serão desativadas.", provider
            )

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
            content = ""
            client = self._client
            if client is None:
                raise RuntimeError("LLM client not available")
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                request_args = dict(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=self._max_output_tokens(),
                    response_format={"type": "json_object"},
                )
                try:
                    response = client.chat.completions.create(**request_args)
                except TypeError:
                    request_args.pop("response_format", None)
                    response = client.chat.completions.create(**request_args)
                content, prompt_tokens, completion_tokens = self._extract_response_payload(response)
            else:  # pragma: no cover - legacy clients
                create = getattr(getattr(client, "ChatCompletion", None), "create", None)
                if not create:
                    raise RuntimeError("OpenAI client incompatível")
                request_args = dict(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "Responda somente em JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self._max_output_tokens(),
                    response_format={"type": "json_object"},
                )
                try:
                    response = create(**request_args)
                except TypeError:
                    request_args.pop("response_format", None)
                    response = create(**request_args)
                content, prompt_tokens, completion_tokens = self._extract_response_payload(response)
            if not content:
                LOGGER.warning("[LLM] Resposta vazia do modelo para %s", title)
                return self._heuristic_summary(title, transcript_clean, max_palavras)
            try:
                finish_reason = None
                if hasattr(response, "choices") and response.choices:
                    first_choice = response.choices[0]
                    finish_reason = getattr(first_choice, "finish_reason", None)
                if finish_reason == "length":
                    LOGGER.warning(
                        "[LLM] Resposta interrompida por limite de tokens para %s; usando heurística.",
                        title,
                    )
                    return self._heuristic_summary(title, transcript_clean, max_palavras)
            except Exception:  # pragma: no cover - defensive, sem efeitos colaterais
                pass
            sanitized = _normalize_json_payload(content)
            if not sanitized:
                raise ValueError("Resposta vazia do modelo.")
            data = json.loads(sanitized)
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
        except json.JSONDecodeError as exc:  # pragma: no cover - depends on API
            LOGGER.warning(
                "[LLM] Resposta não pôde ser convertida para JSON (%s): %s",
                exc,
                _preview(content),
            )
            return self._heuristic_summary(title, transcript_clean, max_palavras)
        except Exception as exc:  # pragma: no cover - depends on API
            LOGGER.warning(
                "[LLM] Erro durante chamada ao modelo: %s — conteúdo: %s",
                exc,
                _preview(content),
            )
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

    def _extract_response_payload(self, response: Any) -> tuple[str, int, int]:
        """Normalize OpenAI SDK responses into text plus token usage."""

        if response is None:
            return "", 0, 0

        content_text = ""
        if hasattr(response, "output_text"):
            content_text = _coerce_to_text(getattr(response, "output_text"))
        if not content_text and hasattr(response, "output"):
            content_text = _coerce_to_text(getattr(response, "output"))
        if not content_text and hasattr(response, "choices"):
            choices = getattr(response, "choices")
            if isinstance(choices, (list, tuple)) and choices:
                first = choices[0]
                message = None
                if isinstance(first, dict):
                    message = first.get("message")
                else:
                    message = getattr(first, "message", None)
                if message is not None:
                    if isinstance(message, dict):
                        content_text = _coerce_to_text(message.get("content"))
                        if not content_text:
                            content_text = _coerce_to_text(message.get("text"))
                    else:
                        message_content = getattr(message, "content", None)
                        content_text = _coerce_to_text(message_content)
                        if not content_text:
                            content_text = _coerce_to_text(getattr(message, "text", None))
                if not content_text:
                    if isinstance(first, dict):
                        content_text = _coerce_to_text(first.get("text"))
                        if not content_text:
                            content_text = _coerce_to_text(first.get("content"))
                    else:
                        content_text = _coerce_to_text(first)
        if not content_text and isinstance(response, dict):
            for key in ("output_text", "output", "choices", "content"):
                if key in response:
                    content_text = _coerce_to_text(response[key])
                    if content_text:
                        break

        content_text = content_text.strip()
        usage = getattr(response, "usage", None)
        if usage is None and isinstance(response, dict):
            usage = response.get("usage")
        prompt_tokens, completion_tokens = _extract_usage_numbers(usage)
        return content_text, prompt_tokens, completion_tokens
