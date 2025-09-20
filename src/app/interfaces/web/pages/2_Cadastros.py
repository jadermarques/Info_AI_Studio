from __future__ import annotations
import streamlit as st
from app.interfaces.web.components import cad_llm, cad_youtube, cad_web

st.title("Cadastros")

tab_llm, tab_youtube, tab_web = st.tabs([
    "Cadastro de LLM",
    "Cadastro Canais YouTube",
    "Cadastro Fontes Web",
])

with tab_llm:
    cad_llm.render()

with tab_youtube:
    cad_youtube.render()

with tab_web:
    cad_web.render()
