"""Página de configurações gerais (parâmetros, banco e backup)."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.domain.parameters_service import update_parameters
from app.infrastructure.backup import create_backup
from app.infrastructure.db import initialize_database, is_database_initialized

st.title("Configurações")
settings = get_settings()

st.subheader("Parâmetros da aplicação")
with st.form("params_form"):
    max_palavras = st.number_input(
        "Máximo de palavras para resumos", min_value=50, max_value=1000, value=settings.max_palavras_resumo
    )
    submitted = st.form_submit_button("Salvar parâmetros")
    if submitted:
        update_parameters({"MAX_PALAVRAS_RESUMO": str(int(max_palavras))})
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
