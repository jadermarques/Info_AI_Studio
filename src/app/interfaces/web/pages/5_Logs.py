"""Visualização de logs e execuções recentes."""

from __future__ import annotations

import streamlit as st
from app.interfaces.web.components.ui_helpers import paginate, render_pagination_controls

from app.config import get_settings
from app.infrastructure import repositories

st.title("Logs")
settings = get_settings()
log_dir = settings.log_dir
log_dir.mkdir(parents=True, exist_ok=True)

log_files = sorted(log_dir.glob("*.log"), reverse=True)
if log_files:
    labels = [f"{path.name}" for path in log_files]
    selected_label = st.selectbox("Selecione um log", options=labels)
    selected_path = log_dir / selected_label
    content = selected_path.read_text(encoding="utf-8") if selected_path.exists() else ""
    st.text_area("Conteúdo do log", value=content, height=400)
else:
    st.info("Nenhum log disponível.")

st.subheader("Histórico de execuções do YouTube")
historico = repositories.list_youtube_extractions(limit=10000)
paginated, page, start, end = paginate(historico, "page_ytex_logs")
st.write(f"Exibindo {start+1} a {end} de {len(historico)}")
render_pagination_controls(
    "page_ytex_logs",
    page,
    end,
    len(historico),
    "ytex_prev",
    "ytex_next",
    size_key="page_ytex_logs_size",
)
if paginated:
    st.dataframe(paginated, hide_index=True, use_container_width=True)
