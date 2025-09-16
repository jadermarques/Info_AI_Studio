"""Dashboard da aplicação com indicadores básicos."""

from __future__ import annotations

import streamlit as st

from app.domain.fonte_service import list_web_sources, list_youtube_channels
from app.domain.llm_service import list_llm_models
from app.infrastructure import repositories

st.title("Dashboard")

llm_models = list_llm_models()
youtube_channels = list_youtube_channels()
web_sources = list_web_sources()
extractions = repositories.list_youtube_extractions(limit=5)

col1, col2, col3 = st.columns(3)
col1.metric("Modelos LLM", len(llm_models))
col2.metric("Canais YouTube", len(youtube_channels))
col3.metric("Fontes Web", len(web_sources))

st.subheader("Últimas execuções do YouTube")
if extractions:
    st.table(extractions)
else:
    st.info("Nenhuma execução registrada até o momento.")

st.subheader("Progresso geral")
st.write(
    "Esta área exibirá relatórios agregados de tokens, custos e utilização assim que as execuções forem realizadas."
)
