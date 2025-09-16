"""Streamlit entrypoint for Info_AI_Studio."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.infrastructure.db import is_database_initialized


def render_home() -> None:
    """Renderiza a página inicial com status gerais."""

    settings = get_settings()
    st.title("Info_AI_Studio")
    st.caption("Coleta e análise de informações em múltiplas fontes")

    db_status = "Conectado" if is_database_initialized() else "Não inicializado"
    llm_status = "Configurada" if settings.llm_api_key else "Não configurada"

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Status do banco de dados", db_status)
        st.page_link("pages/3_Configurações.py", label="Ir para Configurações", icon="⚙️")
    with col2:
        st.metric("Status da LLM", llm_status)
        st.page_link("pages/2_Cadastros.py", label="Ir para Cadastros", icon="🗂️")

    st.divider()
    st.subheader("Ações rápidas")
    st.write("Utilize o menu lateral para navegar entre as páginas da aplicação.")
    st.page_link("pages/4_Execução.py", label="Executar pesquisas", icon="🚀")


def main() -> None:
    """Configura navegação multipage usando st.navigation."""

    st.set_page_config(page_title="Info_AI_Studio", layout="wide")

    navigation = st.navigation(
        {
            "Principal": [st.Page(render_home, title="Home", icon="🏠")],
            "Aplicação": [
                st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊"),
                st.Page("pages/2_Cadastros.py", title="Cadastros", icon="🗂️"),
                st.Page("pages/3_Configurações.py", title="Configurações", icon="⚙️"),
                st.Page("pages/4_Execução.py", title="Execução", icon="🚀"),
                st.Page("pages/5_Logs.py", title="Logs", icon="📝"),
            ],
        }
    )
    navigation.run()


if __name__ == "__main__":
    main()