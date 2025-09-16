"""Página de execução das pesquisas."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import streamlit as st

from app.config import get_settings
from app.domain.entities import YouTubeExtractionConfig
from app.domain.fonte_service import list_youtube_channels
from app.domain.youtube.service import YouTubeExecutionService
from app.infrastructure.db import is_database_initialized

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

st.title("Execução")

st.subheader("Pesquisa Fontes WEB")
st.info(
    "Funcionalidade em desenvolvimento. Aqui serão executadas buscas em sites e blogs registrados."
)
if st.button("Iniciar placeholder", icon="🛠️"):
    st.toast("Execução simulada concluída.")

st.divider()

st.subheader("Pesquisa YouTube")
if not is_database_initialized():
    st.error("Banco de dados não inicializado. Vá até Configurações e execute 'Inicializar banco'.")
else:
    settings = get_settings()
    channels_data = list_youtube_channels(active_only=True)
    options = {
        f"{item['foyt_nome_canal']} ({item['foyt_id_canal']})": item["foyt_id_canal"]
        for item in channels_data
    }
    with st.form("youtube_exec_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected = st.multiselect("Canais cadastrados", options=list(options.keys()))
            manual_entries = st.text_area("Canais adicionais (um por linha)")
            days = st.number_input("Dias para filtrar", min_value=0, max_value=30, value=3)
            max_videos = st.number_input("Limite de vídeos por canal", min_value=0, max_value=200, value=0)
        with col2:
            prefix = st.text_input("Prefixo dos arquivos", value="youtube_extraction")
            report_format = st.selectbox("Formato do relatório", options=["txt", "json", "pdf", "html"], index=0)
            asr_provider = st.selectbox("Fornecedor de ASR", options=["faster-whisper", "openai"])
            no_asr = st.checkbox("Desativar ASR", value=False)
            no_llm = st.checkbox("Desativar LLM", value=not bool(settings.llm_api_key))
            resumo_max = st.number_input(
                "Máximo de palavras no resumo", min_value=50, max_value=1000, value=settings.max_palavras_resumo
            )
            user_agent = st.text_input("User-Agent", value=DEFAULT_USER_AGENT)
            channels_file = st.file_uploader("Arquivo de canais", type=["txt"])
        col_run1, col_run2 = st.columns(2)
        run_simple = col_run1.form_submit_button("Executar modo simple", use_container_width=True)
        run_full = col_run2.form_submit_button("Executar modo full", use_container_width=True)
    if run_simple or run_full:
        mode = "simple" if run_simple else "full"
        channels: list[str] = [options[label] for label in selected]
        if manual_entries:
            channels.extend([line.strip() for line in manual_entries.splitlines() if line.strip()])
        temp_file: Optional[Path] = None
        try:
            if channels_file is not None:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
                tmp.write(channels_file.read())
                tmp.close()
                temp_file = Path(tmp.name)
            config = YouTubeExtractionConfig(
                outdir=(settings.resultados_dir).resolve(),
                prefix=prefix,
                days=int(days) if days else None,
                channels=channels,
                channels_file=temp_file,
                mode=mode,
                no_llm=no_llm,
                asr_enabled=not no_asr,
                asr_provider=asr_provider,
                llm_model=settings.llm_model,
                llm_key=settings.llm_api_key,
                resumo_max_palavras=int(resumo_max),
                cookies=settings.cookies_path,
                user_agent=user_agent,
                report_format=report_format,
                max_videos=int(max_videos) if max_videos else None,
            )
            service = YouTubeExecutionService(config)
            result = service.run()
        except Exception as exc:
            st.error(f"Falha na execução: {exc}")
        else:
            st.success(result.message)
            st.write(f"Canais processados: {result.total_channels}")
            st.write(f"Vídeos extraídos: {result.total_videos}")
            st.write(f"JSON: {result.json_path}")
            if result.report_path:
                st.write(f"Relatório: {result.report_path}")
            st.write(f"Log: {result.log_path}")
        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink(missing_ok=True)