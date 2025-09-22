from __future__ import annotations

"""Serviço de domínio para configurações de consulta via prompt (Fontes Web)."""

from dataclasses import dataclass
from typing import Optional

from app.infrastructure import repositories


@dataclass(slots=True)
class WebPromptDefaults:
    persona: str
    publico_alvo: str
    segmentos: str
    instrucoes: str
    prompt: str


DEFAULT_PERSONA = (
    "um analista sênior de inteligênia de mercado, especializado em Inteligência Artificial e Inteligência Artificial Generativa"
)
DEFAULT_PUBLICO = (
    "consultor de IA que precisa se manter na vanguarda do setor para aconselhar seus clientes"
)
DEFAULT_SEGMENTOS = "{saúde, educação,indústria}"
DEFAULT_INSTRUCOES = ""
DEFAULT_PROMPT = (
    ""  # valor pode ser ajustado pela UI; deixamos vazio por padrão
)


def get_defaults() -> WebPromptDefaults:
    try:
        cfg = repositories.get_web_prompt_config()
    except Exception:
        cfg = None
    if not cfg:
        return WebPromptDefaults(
            persona=DEFAULT_PERSONA,
            publico_alvo=DEFAULT_PUBLICO,
            segmentos=DEFAULT_SEGMENTOS,
            instrucoes=DEFAULT_INSTRUCOES,
            prompt=DEFAULT_PROMPT,
        )
    return WebPromptDefaults(
        persona=cfg.get("wpc_persona") or DEFAULT_PERSONA,
        publico_alvo=cfg.get("wpc_publico_alvo") or DEFAULT_PUBLICO,
        segmentos=cfg.get("wpc_segmentos") or DEFAULT_SEGMENTOS,
        instrucoes=cfg.get("wpc_instrucoes") or DEFAULT_INSTRUCOES,
        prompt=cfg.get("wpc_prompt") or DEFAULT_PROMPT,
    )


def save_defaults(values: WebPromptDefaults) -> None:
    repositories.upsert_web_prompt_config(
        persona=values.persona,
        publico_alvo=values.publico_alvo,
        segmentos=values.segmentos,
        instrucoes=values.instrucoes,
        prompt=values.prompt,
    )
