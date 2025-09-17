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


def _parse_json_fragment(text: str) -> Optional[Any]:
    """Return the first JSON object/array found in text, ignoring trailing data."""

    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        try:
            data, _ = decoder.raw_decode(text)
            return data
        except json.JSONDecodeError:
            return None


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
        translate_mode: str,
    ) -> LLMResult:
        """Generate a structured summary for a transcript."""

        transcript_clean = transcript.strip()
        if not transcript_clean:
            LOGGER.info("[LLM] Transcrição vazia — pulando análise para %s", title)
            return LLMResult("", "", "", [], "", 0, 0, self.model, 0.0)
        if not self.active:
            LOGGER.info("[LLM] Cliente LLM ausente — usando resumo heurístico.")
            return self._heuristic_summary(title, transcript_clean, max_palavras)
        excerpt_limits = (8000, 6000, 4000, 2500, 1500, 900, 600)
        last_exception: Exception | None = None
        translate_normalized = "pt-br" if translate_mode.lower() in {"pt", "pt-br", "pt_br", "portugues", "português", "br"} else "original"
        LOGGER.debug("[LLM] Processo de resumo para '%s' com translate_mode=%s", title, translate_normalized)
        for index, excerpt_limit in enumerate(excerpt_limits):
            prompt = self._build_prompt(
                title,
                channel,
                transcript_clean,
                max_palavras,
                excerpt_limit,
                translate_normalized,
            )
            try:
                content, prompt_tokens, completion_tokens, finish_reason = self._request_completion(
                    prompt, translate_normalized
                )
                LOGGER.debug(
                    "[LLM] Tentativa %s com trecho %s chars — finish_reason=%s, prompt_tokens=%s, completion_tokens=%s",
                    index + 1,
                    excerpt_limit,
                    finish_reason,
                    prompt_tokens,
                    completion_tokens,
                )
            except Exception as exc:  # pragma: no cover - depends on API
                last_exception = exc
                LOGGER.warning(
                    "[LLM] Erro durante chamada ao modelo (trecho %s chars): %s",
                    excerpt_limit,
                    exc,
                )
                continue
            if not content:
                LOGGER.warning("[LLM] Resposta vazia do modelo para %s (trecho %s chars)", title, excerpt_limit)
                continue
            truncated = finish_reason == "length"
            if truncated and index < len(excerpt_limits) - 1:
                LOGGER.warning(
                    "[LLM] Resumo truncado (finish_reason=length) para %s; reduzindo transcrição para %s chars.",
                    title,
                    excerpt_limits[index + 1],
                )
                continue
            sanitized = _normalize_json_payload(content)
            if not sanitized:
                LOGGER.warning(
                    "[LLM] Resposta sem JSON utilizável para %s (trecho %s chars): %s",
                    title,
                    excerpt_limit,
                    _preview(content),
                )
                if truncated and index < len(excerpt_limits) - 1:
                    continue
                break
            data = _parse_json_fragment(sanitized)
            if data is None:
                LOGGER.warning(
                    "[LLM] Resposta não pôde ser convertida para JSON (trecho %s): %s",
                    excerpt_limit,
                    _preview(content),
                )
                if truncated and index < len(excerpt_limits) - 1:
                    continue
                break
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    data = first
            if not isinstance(data, dict):
                LOGGER.warning(
                    "[LLM] Resposta com estrutura %s ignorada para %s",
                    type(data).__name__ if data is not None else "None",
                    title,
                )
                continue
            result = LLMResult(
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
            if translate_normalized == "pt-br":
                result = self._translate_result_fields(result)
            return result
            if truncated and index == len(excerpt_limits) - 1:
                LOGGER.warning(
                    "[LLM] Resposta interrompida por limite de tokens para %s; usando heurística.",
                    title,
                )
                break
        if last_exception:
            LOGGER.warning("[LLM] Falha na chamada após múltiplas tentativas: %s", last_exception)
        heuristic = self._heuristic_summary(title, transcript_clean, max_palavras)
        if translate_normalized == "pt-br":
            heuristic = self._translate_result_fields(heuristic)
        return heuristic

    def _build_prompt(
        self,
        title: str,
        channel: str,
        transcript: str,
        max_palavras: int,
        excerpt_limit: int,
        language_mode: str,
    ) -> str:
        snippet = transcript[: min(len(transcript), excerpt_limit)]
        if language_mode == "pt-br":
            language_instruction = "Traduza todos os campos do JSON para Português (Brasil)."
        else:
            language_instruction = "Mantenha os campos na mesma língua da transcrição, sem traduzir."
        return (
            "Você é um analista. Resuma a transcrição de um vídeo do YouTube.\n"
            f"Título: {title}\n"
            f"Canal: {channel}\n"
            f"Transcrição: {snippet}\n"
            f"{language_instruction}\n"
            "Responda em JSON válido com as chaves: resumo_do_video_uma_frase,"
            " resumo_do_video, assunto_principal, palavras_chave (lista) e resumo_em_topicos (Markdown)."
            f" Limite o campo resumo_do_video a {max_palavras} palavras."
        )

    def _request_completion(
        self,
        prompt: str,
        language_mode: str,
        system_instruction: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        expect_json: bool = True,
    ) -> tuple[str, int, int, Optional[str]]:
        client = self._client
        if client is None:
            raise RuntimeError("LLM client not available")
        content = ""
        prompt_tokens = 0
        completion_tokens = 0
        finish_reason: Optional[str] = None
        if system_instruction:
            instruction = system_instruction
        else:
            if expect_json:
                instruction = "Responda somente em JSON."
                if language_mode == "pt-br":
                    instruction += " Todos os campos devem estar em Português (Brasil), traduzindo se necessário."
                else:
                    instruction += " Mantenha todos os campos na língua original, sem tradução."
            else:
                instruction = (
                    "Forneça a resposta apenas como texto corrido, sem comentários adicionais."
                    " Utilize Português (Brasil) sempre que possível."
                )
        output_limit = max_output_tokens or self._max_output_tokens()
        if hasattr(client, "chat") and hasattr(client.chat, "completions"):
            request_args = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=output_limit,
            )
            if expect_json:
                request_args["response_format"] = {"type": "json_object"}
            try:
                response = client.chat.completions.create(**request_args)
            except TypeError:
                request_args.pop("response_format", None)
                response = client.chat.completions.create(**request_args)
            content, prompt_tokens, completion_tokens, finish_reason = self._extract_response_payload(response)
        else:  # pragma: no cover - legacy clients
            create = getattr(getattr(client, "ChatCompletion", None), "create", None)
            if not create:
                raise RuntimeError("OpenAI client incompatível")
            request_args = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=output_limit,
            )
            if expect_json:
                request_args["response_format"] = {"type": "json_object"}
            try:
                response = create(**request_args)
            except TypeError:
                request_args.pop("response_format", None)
                response = create(**request_args)
            content, prompt_tokens, completion_tokens, finish_reason = self._extract_response_payload(response)
        return content, prompt_tokens, completion_tokens, finish_reason

    def _translate_result_fields(self, result: LLMResult) -> LLMResult:
        client = self._client
        if client is None:
            return result
        payload = {
            "resumo_do_video_uma_frase": result.resumo_uma_frase,
            "resumo_do_video": result.resumo,
            "assunto_principal": result.assunto_principal,
            "palavras_chave": result.palavras_chave,
            "resumo_em_topicos": result.resumo_em_topicos,
        }
        data = self._bulk_translate_payload(payload)
        if data is None:
            LOGGER.debug("[LLM] Tradução coletiva falhou; iniciando fallback campo a campo")
            return self._translate_fields_individually(result)
        palavras_raw = data.get("palavras_chave", result.palavras_chave)
        if isinstance(palavras_raw, list):
            palavras = [str(item) for item in palavras_raw if item not in (None, "")]
        elif isinstance(palavras_raw, str):
            palavras = [item.strip() for item in palavras_raw.split(",") if item.strip()]
        else:
            palavras = result.palavras_chave
        return LLMResult(
            resumo_uma_frase=str(data.get("resumo_do_video_uma_frase", result.resumo_uma_frase)),
            resumo=str(data.get("resumo_do_video", result.resumo)),
            assunto_principal=str(data.get("assunto_principal", result.assunto_principal)),
            palavras_chave=palavras,
            resumo_em_topicos=str(data.get("resumo_em_topicos", result.resumo_em_topicos)),
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            model=result.model,
            cost=result.cost,
        )

    def _bulk_translate_payload(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        prompt = (
            "Traduza o JSON a seguir para Português (Brasil), mantendo as mesmas chaves e retornando JSON válido.\n"
            f"JSON: {json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            LOGGER.debug(
                "[LLM] Solicitando tradução adicional para pt-br (tamanho resumo=%s)",
                len(str(payload.get("resumo_do_video", ""))),
            )
            content, _, _, _ = self._request_completion(
                prompt,
                language_mode="pt-br",
                system_instruction=(
                    "Você é um tradutor profissional. Retorne apenas JSON válido com as mesmas chaves,"
                    " traduzindo todo o conteúdo textual para Português (Brasil)."
                ),
                max_output_tokens=768,
                expect_json=True,
            )
            sanitized = _normalize_json_payload(content)
            if not sanitized:
                return None
            data = _parse_json_fragment(sanitized)
            if isinstance(data, dict):
                return data
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    return first
            LOGGER.warning(
                "[LLM] Tradução retornou estrutura não suportada: %s",
                type(data).__name__ if data is not None else "None",
            )
        except Exception as exc:  # pragma: no cover - depende da API
            LOGGER.warning("[LLM] Falha ao traduzir resultado para pt-br: %s", exc)
        return None

    def _translate_fields_individually(self, result: LLMResult) -> LLMResult:
        resumo_uma_frase = self._translate_text_field("resumo_uma_frase", result.resumo_uma_frase)
        resumo = self._translate_text_field("resumo", result.resumo)
        assunto = self._translate_text_field("assunto", result.assunto_principal)
        topicos = self._translate_text_field("topicos", result.resumo_em_topicos)
        palavras = self._translate_keywords(result.palavras_chave)
        return LLMResult(
            resumo_uma_frase=resumo_uma_frase,
            resumo=resumo,
            assunto_principal=assunto,
            palavras_chave=palavras,
            resumo_em_topicos=topicos,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            model=result.model,
            cost=result.cost,
        )

    def _translate_text_field(self, label: str, text: str) -> str:
        if not text.strip():
            return text
        truncated = text[:4000]
        prompt = (
            f"Traduza o texto a seguir para Português (Brasil) e responda em JSON válido no formato"
            f" {{\"{label}\": \"...\"}}.\nTexto: {truncated}"
        )
        try:
            content, _, _, _ = self._request_completion(
                prompt,
                language_mode="pt-br",
                max_output_tokens=512,
                expect_json=True,
            )
            sanitized = _normalize_json_payload(content)
            if not sanitized:
                return self._simple_translate_text(truncated)
            data = _parse_json_fragment(sanitized)
            if isinstance(data, list) and data:
                data = data[0]
            if not isinstance(data, dict):
                return self._simple_translate_text(truncated)
            value = data.get(label)
            if value not in (None, ""):
                return str(value)
            return self._simple_translate_text(truncated)
        except Exception as exc:  # pragma: no cover - depende da API
            LOGGER.warning("[LLM] Falha ao traduzir campo %s: %s", label, exc)
            return self._simple_translate_text(truncated)

    def _translate_keywords(self, keywords: list[str]) -> list[str]:
        if not keywords:
            return keywords
        prompt = (
            "Traduza cada termo da lista para Português (Brasil) mantendo uma lista de strings."
            f" Retorne JSON válido no formato {{\"palavras\": [...]}}. Lista: {json.dumps(keywords, ensure_ascii=False)}"
        )
        try:
            content, _, _, _ = self._request_completion(
                prompt,
                language_mode="pt-br",
                max_output_tokens=512,
                expect_json=True,
            )
            sanitized = _normalize_json_payload(content)
            if not sanitized:
                return self._simple_translate_keywords(keywords)
            data = _parse_json_fragment(sanitized)
            if isinstance(data, list) and data:
                data = data[0]
            if not isinstance(data, dict):
                return self._simple_translate_keywords(keywords)
            palavras = data.get("palavras")
            if isinstance(palavras, list):
                return [str(item) for item in palavras if item not in (None, "")]
            if isinstance(palavras, str):
                return [item.strip() for item in palavras.split(",") if item.strip()]
        except Exception as exc:  # pragma: no cover - depende da API
            LOGGER.warning("[LLM] Falha ao traduzir palavras-chave: %s", exc)
        return self._simple_translate_keywords(keywords)

    def _simple_translate_text(self, text: str) -> str:
        if not text.strip():
            return text
        prompt = (
            "Traduza o texto a seguir para Português (Brasil). Responda apenas com o texto traduzido,"
            " sem comentários adicionais.\nTexto: " + text[:4000]
        )
        try:
            content, _, _, _ = self._request_completion(
                prompt,
                language_mode="pt-br",
                max_output_tokens=512,
                expect_json=False,
                system_instruction=(
                    "Você é um tradutor. Responda apenas com o texto traduzido em Português (Brasil),"
                    " sem aspas ou formatação adicional."
                ),
            )
            translated = content.strip()
            return translated or text
        except Exception as exc:  # pragma: no cover - depende da API
            LOGGER.warning("[LLM] Falha na tradução simples: %s", exc)
            return text

    def _simple_translate_keywords(self, keywords: list[str]) -> list[str]:
        joined = ", ".join(keywords)
        prompt = (
            "Traduza cada termo da lista para Português (Brasil). Responda apenas com os termos separados por vírgula."
            f"\nLista: {joined}"
        )
        try:
            content, _, _, _ = self._request_completion(
                prompt,
                language_mode="pt-br",
                max_output_tokens=256,
                expect_json=False,
                system_instruction=(
                    "Você é um tradutor. Responda apenas com os termos traduzidos separados por vírgula"
                    " em Português (Brasil), sem texto extra."
                ),
            )
            translated = content.strip()
            if translated:
                return [item.strip() for item in translated.split(",") if item.strip()]
        except Exception as exc:  # pragma: no cover - depende da API
            LOGGER.warning("[LLM] Falha na tradução simples de palavras-chave: %s", exc)
        return keywords

    def _heuristic_summary(
        self, title: str, transcript: str, max_palavras: int
    ) -> LLMResult:
        """Generate a lightweight summary when no LLM is available."""

        words = transcript.split()
        filtered_words = [
            word
            for word in words
            if not (word.startswith("[") and word.endswith("]"))
        ]
        if filtered_words:
            words = filtered_words
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

        # Permite que o modelo tenha espaço suficiente para tópicos e resumos completos
        upper_bound = max(512, math.ceil(self.token_limit * 0.5))
        return min(2048, upper_bound)

    def _extract_response_payload(self, response: Any) -> tuple[str, int, int, Optional[str]]:
        """Normalize OpenAI SDK responses into text, token usage and finish reason."""

        if response is None:
            return "", 0, 0, None

        content_text = ""
        finish_reason: Optional[str] = None
        if hasattr(response, "output_text"):
            content_text = _coerce_to_text(getattr(response, "output_text"))
        if not content_text and hasattr(response, "output"):
            content_text = _coerce_to_text(getattr(response, "output"))
        if not content_text and hasattr(response, "choices"):
            choices = getattr(response, "choices")
            if isinstance(choices, (list, tuple)) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    finish_reason = first.get("finish_reason") or finish_reason
                else:
                    finish_reason = getattr(first, "finish_reason", finish_reason)
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
        return content_text, prompt_tokens, completion_tokens, finish_reason
