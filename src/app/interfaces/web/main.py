"""Streamlit entrypoint for Info_AI_Studio."""

from __future__ import annotations

import streamlit as st

from app.config import get_settings
from app.infrastructure.db import is_database_initialized


def _status_indicator(label: str, connected: bool, connected_text: str, disconnected_text: str) -> None:
    """Render a traffic-light style indicator for connection status."""

    color = "#22c55e" if connected else "#ef4444"
    status_text = connected_text if connected else disconnected_text
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0.75rem;padding:0.5rem 0;">
            <span style="width:0.9rem;height:0.9rem;border-radius:50%;background:{color};display:inline-block;"></span>
            <div style="display:flex;flex-direction:column;">
                <span style="font-weight:600;font-size:0.95rem;color:#1f2937;">{label}</span>
                <span style="font-weight:700;color:{color};letter-spacing:0.02em;">{status_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home() -> None:
    """Renderiza a página inicial com status gerais."""

    settings = get_settings()
    st.title("Info_AI_Studio")
    st.caption("Coleta e análise de informações em múltiplas fontes")

    db_connected = is_database_initialized()
    llm_connected = bool(settings.llm_api_key)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Banco de dados")
        _status_indicator("Status do banco", db_connected, "CONECTADO", "NÃO CONECTADO")
        st.page_link("pages/3_Configurações.py", label="Ir para Configurações", icon="⚙️")
    with col2:
        st.subheader("Modelo LLM")
        _status_indicator("Status da LLM", llm_connected, "CONECTADO", "NÃO CONFIGURADO")
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
                st.Page("pages/6_Resultados.py", title="Resultados", icon="📁"),
                st.Page("pages/5_Logs.py", title="Logs", icon="📝"),
            ],
        }
    )
    navigation.run()


if __name__ == "__main__":
    main()
