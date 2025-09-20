"""Página de configurações gerais (parâmetros, banco e backup)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Optional

import streamlit as st

from app.config import get_settings, reload_settings
from app.infrastructure.backup import create_backup
from app.infrastructure.db import initialize_database, is_database_initialized
from app.infrastructure.env_manager import update_env_values

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
    if st.button("Inicializar banco", use_container_width=True):
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
