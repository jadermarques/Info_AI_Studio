"""Página de configurações gerais (parâmetros, banco e backup)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Optional

import streamlit as st

from app.config import get_settings, reload_settings
from app.infrastructure.backup import create_backup
from app.infrastructure.db import initialize_database, is_database_initialized
from app.infrastructure.env_manager import update_env_values
from app.domain.web_prompt_execution import WebPromptParams, _build_prompt_text
from app.domain.web_prompt_service import (
    get_defaults as web_get_defaults,
    save_defaults as web_save_defaults,
    WebPromptDefaults,
)

_domain_update_parameters: Optional[Callable[[Mapping[str, str]], object]]
_domain_import_error: Optional[Exception]
try:  # pragma: no cover - defensive fallback for partially installed packages
    from app.domain.parameters_service import update_parameters as _domain_update_parameters
except Exception as exc:  # pragma: no cover - catch any import-time failure
    _domain_update_parameters = None
    _domain_import_error = exc
else:
    _domain_import_error = None


def _persist_parameters(values: Mapping[str, str]) -> None:
    """Persist parameters via the domain service or fallback directly to .env."""

    if _domain_update_parameters is not None:
        _domain_update_parameters(values)
        return

    update_env_values(values)
    reload_settings()
    st.info("Parâmetros atualizados usando fallback direto no arquivo .env.")


st.title("Configurações")
settings = get_settings()

if _domain_update_parameters is None:
    message = "Serviço de parâmetros indisponível; utilizando fallback direto no arquivo .env."
    if _domain_import_error is not None:
        message += f" (motivo: {type(_domain_import_error).__name__}: {_domain_import_error})"
    st.warning(message)

st.subheader("Parâmetros da aplicação")
TRANSLATE_OPTIONS = {
    "Linguagem original": "original",
    "Português (Brasil)": "pt-br",
}
with st.form("params_form"):
    max_palavras = st.number_input(
        "Máximo de palavras para resumos", min_value=50, max_value=1000, value=settings.max_palavras_resumo
    )
    translate_default_label = next(
        (label for label, value in TRANSLATE_OPTIONS.items() if value == settings.translate_results),
        "Linguagem original",
    )
    translate_label = st.selectbox(
        "Traduzir resultados",
        options=list(TRANSLATE_OPTIONS.keys()),
        index=list(TRANSLATE_OPTIONS.keys()).index(translate_default_label),
    )
    user_agent = st.text_input(
        "User-Agent padrão para YouTube",
        value=settings.user_agent,
        help="Cabeçalho User-Agent utilizado em requisições de scraping.",
    )
    submitted = st.form_submit_button("Salvar parâmetros")
    if submitted:
        _persist_parameters(
            {
                "MAX_PALAVRAS_RESUMO": str(int(max_palavras)),
                "TRANSLATE_RESULTS": TRANSLATE_OPTIONS[translate_label],
                "USER_AGENT": user_agent.strip(),
            }
        )
        st.success("Parâmetros atualizados.")
        st.rerun()

st.divider()

st.subheader("Banco de dados")
col_a, col_b = st.columns(2)
with col_a:
    st.metric("Status", "Conectado" if is_database_initialized() else "Não inicializado")
with col_b:
    if st.button("Inicializar banco", width='stretch'):
        initialize_database()
        st.success("Banco inicializado com sucesso.")
        st.rerun()

st.divider()

st.subheader("Backup do banco")
if st.button("Gerar backup", icon="💾"):
    try:
        backup_path = create_backup()
    except FileNotFoundError as exc:
        st.error(str(exc))
    else:
        st.success(f"Backup gerado em {backup_path}")

st.divider()

st.subheader("Configurações da consulta Info Web (campos via prompt)")
web_defaults = web_get_defaults()
# Mensagem de sucesso pós-salvamento (sobrevive ao rerun)
if st.session_state.get("web_prompt_saved"):
    st.success("Configurações salvas com sucesso.")
    del st.session_state["web_prompt_saved"]
with st.form("web_prompt_defaults_form"):
    col1, col2 = st.columns(2)
    with col1:
        persona = st.text_input(
            "Persona (padrão)",
            value=web_defaults.persona,
            help="Valor padrão exibido na aba Execução > Fontes Web > Consulta via prompt.",
        )
        publico = st.text_input(
            "Público-alvo (padrão)",
            value=web_defaults.publico_alvo,
        )
    with col2:
        segmentos = st.text_input(
            "Segmentos (padrão)",
            value=web_defaults.segmentos,
            help="Ex.: {saúde, educação,indústria}",
        )
    prompt_padrao = st.text_area(
        "Prompt da consulta (padrão)",
        value=web_defaults.prompt,
        height=280,
        help="Texto base do prompt exibido por padrão na execução (o usuário pode alterar somente para aquela execução).",
    )
    if st.form_submit_button("Salvar configurações de consulta web", width='stretch'):
        web_save_defaults(
            WebPromptDefaults(
                persona=persona.strip(),
                publico_alvo=publico.strip(),
                segmentos=segmentos.strip(),
                instrucoes=(web_defaults.instrucoes or "").strip(),
                prompt=prompt_padrao,
            )
        )
        st.session_state["web_prompt_saved"] = True
        st.rerun()

        # Prévia do prompt final (com variáveis aplicadas)
        st.markdown("Prévia do prompt final (com variáveis preenchidas)")
        from datetime import date as _date, timedelta
        prev_col1, prev_col2, prev_col3 = st.columns([1,1,1])
        with prev_col1:
            prev_dt_inicio = st.date_input("Data de início (prévia)", value=_date.today(), format="DD/MM/YYYY", key="web_prev_dt_inicio")
        with prev_col2:
            prev_dt_fim = st.date_input("Data de término (prévia)", value=_date.today() + timedelta(days=7), format="DD/MM/YYYY", key="web_prev_dt_fim")
        with prev_col3:
            prev_formato = st.selectbox(
                "Formato (texto)",
                options=["Markdown", "Texto", "JSON", "XML", "PDF"],
                index=0,
                help="Somente para visualização da prévia.",
                key="web_prev_formato_texto",
            )

        # Usa sempre os valores atualmente carregados (padrões salvos)
        _defaults = web_get_defaults()
        _params = WebPromptParams(
            data_inicio=prev_dt_inicio,
            data_fim=prev_dt_fim,
            persona=_defaults.persona,
            publico_alvo=_defaults.publico_alvo,
            segmentos=_defaults.segmentos,
            instrucoes=_defaults.instrucoes,
            prompt_base=_defaults.prompt,
            formato_saida=prev_formato,
            llm_provedor="OPENAI",
            llm_modelo="gpt-4o-mini",
            api_key="",
            outdir=settings.resultados_dir,
        )
        _preview_text = _build_prompt_text(_params)
        with st.expander("Ver prévia do prompt", expanded=True):
            st.code(_preview_text, language="markdown")
