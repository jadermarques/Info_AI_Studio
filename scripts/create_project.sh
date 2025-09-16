 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/src/app/domain/llm_client.py b/src/app/domain/llm_client.py
index 8b16a69b7c5e590940e8032d017719e11c95f4c6..cac159f951dae2bb95a77119a5f43cccd008f741 100644
--- a/src/app/domain/llm_client.py
+++ b/src/app/domain/llm_client.py
@@ -1,37 +1,113 @@
 """LLM client abstraction used to summarise video transcripts."""
 
 from __future__ import annotations
 
 import json
 import logging
 import math
 from dataclasses import dataclass
-from typing import Optional
+from typing import Any, Optional
 
 LOGGER = logging.getLogger(__name__)
 
+
+def _safe_int(value: Any) -> int:
+    """Convert values that might be None/str/float into integers safely."""
+
+    if value in (None, ""):
+        return 0
+    if isinstance(value, bool):
+        return int(value)
+    if isinstance(value, (int, float)):
+        return int(value)
+    try:
+        text = str(value).strip()
+        if not text:
+            return 0
+        return int(float(text))
+    except (TypeError, ValueError):
+        return 0
+
+
+def _coerce_to_text(value: Any) -> str:
+    """Extract textual content from heterogeneous OpenAI SDK objects."""
+
+    if value in (None, ""):
+        return ""
+    if isinstance(value, str):
+        return value
+    if isinstance(value, (list, tuple, set)):
+        return "".join(_coerce_to_text(item) for item in value)
+    if isinstance(value, dict):
+        for key in ("text", "content", "value", "message"):
+            if key in value:
+                text = _coerce_to_text(value[key])
+                if text:
+                    return text
+        # fallback: concatenate string values if present
+        parts = [str(item) for item in value.values() if isinstance(item, str)]
+        return " ".join(parts)
+    for attr in ("text", "value", "content"):
+        if hasattr(value, attr):
+            attr_value = getattr(value, attr)
+            if attr_value is not value:
+                text = _coerce_to_text(attr_value)
+                if text:
+                    return text
+    return str(value)
+
+
+def _extract_usage_numbers(usage: Any) -> tuple[int, int]:
+    """Retrieve prompt and completion tokens from different usage schemas."""
+
+    if usage is None:
+        return 0, 0
+
+    def _read(keys: tuple[str, ...]) -> int:
+        for key in keys:
+            if isinstance(usage, dict):
+                value = usage.get(key)
+            else:
+                value = getattr(usage, key, None)
+            if value is not None:
+                return _safe_int(value)
+        return 0
+
+    prompt_tokens = _read(("prompt_tokens", "input_tokens"))
+    completion_tokens = _read(("completion_tokens", "output_tokens"))
+    total_tokens = _read(("total_tokens",))
+
+    if not completion_tokens and total_tokens and prompt_tokens:
+        completion_tokens = max(0, total_tokens - prompt_tokens)
+    elif not completion_tokens and total_tokens:
+        completion_tokens = total_tokens
+    if not prompt_tokens and total_tokens and completion_tokens:
+        prompt_tokens = max(0, total_tokens - completion_tokens)
+
+    return prompt_tokens, completion_tokens
+
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
diff --git a/src/app/domain/llm_client.py b/src/app/domain/llm_client.py
index 8b16a69b7c5e590940e8032d017719e11c95f4c6..cac159f951dae2bb95a77119a5f43cccd008f741 100644
--- a/src/app/domain/llm_client.py
+++ b/src/app/domain/llm_client.py
@@ -78,92 +154,137 @@ class LLMClient:
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
-                content = response.choices[0].message.content if response.choices else ""
-                usage = getattr(response, "usage", None)
-                prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
-                completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
+                content, prompt_tokens, completion_tokens = self._extract_response_payload(response)
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
-                content = response["choices"][0]["message"]["content"] if response else ""
-                usage = response.get("usage", {}) if isinstance(response, dict) else {}
-                prompt_tokens = usage.get("prompt_tokens", 0)
-                completion_tokens = usage.get("completion_tokens", 0)
+                content, prompt_tokens, completion_tokens = self._extract_response_payload(response)
             if not content:
                 LOGGER.warning("[LLM] Resposta vazia do modelo para %s", title)
-                return LLMResult("", "", "", [], "", 0, 0, self.model, 0.0)
+                return self._heuristic_summary(title, transcript_clean, max_palavras)
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
+
+    def _extract_response_payload(self, response: Any) -> tuple[str, int, int]:
+        """Normalize OpenAI SDK responses into text plus token usage."""
+
+        if response is None:
+            return "", 0, 0
+
+        content_text = ""
+        if hasattr(response, "output_text"):
+            content_text = _coerce_to_text(getattr(response, "output_text"))
+        if not content_text and hasattr(response, "output"):
+            content_text = _coerce_to_text(getattr(response, "output"))
+        if not content_text and hasattr(response, "choices"):
+            choices = getattr(response, "choices")
+            if isinstance(choices, (list, tuple)) and choices:
+                first = choices[0]
+                message = None
+                if isinstance(first, dict):
+                    message = first.get("message")
+                else:
+                    message = getattr(first, "message", None)
+                if message is not None:
+                    if isinstance(message, dict):
+                        content_text = _coerce_to_text(message.get("content"))
+                        if not content_text:
+                            content_text = _coerce_to_text(message.get("text"))
+                    else:
+                        message_content = getattr(message, "content", None)
+                        content_text = _coerce_to_text(message_content)
+                        if not content_text:
+                            content_text = _coerce_to_text(getattr(message, "text", None))
+                if not content_text:
+                    if isinstance(first, dict):
+                        content_text = _coerce_to_text(first.get("text"))
+                        if not content_text:
+                            content_text = _coerce_to_text(first.get("content"))
+                    else:
+                        content_text = _coerce_to_text(first)
+        if not content_text and isinstance(response, dict):
+            for key in ("output_text", "output", "choices", "content"):
+                if key in response:
+                    content_text = _coerce_to_text(response[key])
+                    if content_text:
+                        break
+
+        content_text = content_text.strip()
+        usage = getattr(response, "usage", None)
+        if usage is None and isinstance(response, dict):
+            usage = response.get("usage")
+        prompt_tokens, completion_tokens = _extract_usage_numbers(usage)
+        return content_text, prompt_tokens, completion_tokens
 
EOF
)