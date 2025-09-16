"""Página de cadastros (LLM, canais e fontes)."""

from __future__ import annotations

import streamlit as st

from app.domain.entities import LLMModel, WebSource, YouTubeChannel
from app.domain.fonte_service import (
    list_web_sources,
    list_youtube_channels,
    register_web_source,
    register_youtube_channel,
)
from app.domain.llm_service import list_llm_models, register_llm_model

st.title("Cadastros")

st.subheader("Modelos LLM")
with st.form("llm_form"):
    col1, col2 = st.columns(2)
    with col1:
        provedor = st.text_input("Provedor", placeholder="OPENAI")
        modelo = st.text_input("Modelo", placeholder="gpt-5-nano")
    with col2:
        api_key = st.text_input("API Key", type="password")
        ativo = st.checkbox("Ativo", value=True)
    submitted = st.form_submit_button("Salvar modelo")
    if submitted:
        if not provedor or not modelo or not api_key:
            st.error("Informe provedor, modelo e API key.")
        else:
            register_llm_model(
                LLMModel(provedor=provedor, modelo=modelo, api_key=api_key, status=ativo)
            )
            st.success("Modelo salvo com sucesso.")
            st.rerun()

st.table(list_llm_models())

st.divider()

st.subheader("Canais do YouTube")
with st.form("youtube_form"):
    nome = st.text_input("Nome do canal")
    descricao = st.text_area("Descrição")
    grupo = st.text_input("Grupo do canal")
    canal_id = st.text_input("ID do canal", placeholder="@exemplo")
    ativo_canal = st.checkbox("Ativo", value=True)
    submit_channel = st.form_submit_button("Salvar canal")
    if submit_channel:
        if not nome or not descricao or not grupo or not canal_id:
            st.error("Todos os campos são obrigatórios.")
        else:
            register_youtube_channel(
                YouTubeChannel(
                    nome=nome,
                    descricao=descricao,
                    grupo=grupo,
                    canal_id=canal_id,
                    status=ativo_canal,
                )
            )
            st.success("Canal salvo com sucesso.")
            st.rerun()

st.table(list_youtube_channels(active_only=False))

st.divider()

st.subheader("Fontes Web")
with st.form("web_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        tipo = st.selectbox("Tipo", options=["site", "blog", "youtube"])
        status = st.checkbox("Ativo", value=True)
    with col_b:
        fonte = st.text_input("Fonte", placeholder="https://exemplo.com")
    descricao_fonte = st.text_area("Descrição")
    submit_web = st.form_submit_button("Salvar fonte")
    if submit_web:
        if not fonte or not descricao_fonte:
            st.error("Fonte e descrição são obrigatórias.")
        else:
            try:
                register_web_source(
                    WebSource(tipo=tipo, fonte=fonte, descricao=descricao_fonte, status=status)
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success("Fonte registrada com sucesso.")
                st.rerun()

st.table(list_web_sources(active_only=False))
