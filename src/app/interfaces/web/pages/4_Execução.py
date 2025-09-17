"""Página de execução das pesquisas."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.config import get_settings
from app.domain.entities import YouTubeExtractionConfig
from app.domain.fonte_service import list_youtube_channels
from app.domain.llm_service import list_llm_models
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
    llm_models = [model for model in list_llm_models() if model["status"]]
    llm_options = {
        f"{model['provedor']} - {model['modelo']}": model for model in llm_models
    }
    if not llm_options:
        st.warning(
            "Nenhum modelo LLM ativo encontrado. Cadastre um modelo antes de executar a pesquisa."
        )
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
            llm_label = st.selectbox(
                "Modelo LLM",
                options=list(llm_options.keys()),
                disabled=not llm_options,
            )
            resumo_max = st.number_input(
                "Máximo de palavras no resumo", min_value=50, max_value=1000, value=settings.max_palavras_resumo
            )
            user_agent = st.text_input("User-Agent", value=DEFAULT_USER_AGENT)
        col_run1, col_run2 = st.columns(2)
        disabled_buttons = not llm_options
        run_simple = col_run1.form_submit_button(
            "Executar modo simple", use_container_width=True, disabled=disabled_buttons
        )
        run_full = col_run2.form_submit_button(
            "Executar modo full", use_container_width=True, disabled=disabled_buttons
        )
    progress_container = st.container()
    results_container = st.container()
    if run_simple or run_full:
        mode = "simple" if run_simple else "full"
        channels: list[str] = [options[label] for label in selected]
        if manual_entries:
            channels.extend([line.strip() for line in manual_entries.splitlines() if line.strip()])
        if not selected:
            st.error("Selecione ao menos um canal cadastrado para executar a pesquisa.")
            st.stop()
        if not channels:
            st.error("Nenhum canal válido informado.")
            st.stop()
        if not llm_label:
            st.error("Selecione um modelo LLM para continuar.")
            st.stop()
        selected_model = llm_options.get(llm_label)
        if not selected_model or not selected_model.get("api_key"):
            st.error("O modelo LLM selecionado não possui uma chave de API válida.")
            st.stop()
        progress_messages: list[str] = []
        progress_placeholder = progress_container.empty()

        def update_progress(message: str) -> None:
            progress_messages.append(message)
            formatted = "\n".join(f"- {msg}" for msg in progress_messages)
            progress_placeholder.markdown(formatted or "- Aguardando início da execução...")

        update_progress("Preparando execução...")
        try:
            config = YouTubeExtractionConfig(
                outdir=(settings.resultados_dir).resolve(),
                prefix=prefix,
                days=int(days) if days else None,
                channels=channels,
                channels_file=None,
                mode=mode,
                no_llm=False,
                asr_enabled=not no_asr,
                asr_provider=asr_provider,
                llm_provider=selected_model.get("provedor"),
                llm_model=selected_model.get("modelo", settings.llm_model),
                llm_key=selected_model.get("api_key"),
                resumo_max_palavras=int(resumo_max),
                cookies=settings.cookies_path,
                user_agent=user_agent,
                report_format=report_format,
                max_videos=int(max_videos) if max_videos else None,
            )
            service = YouTubeExecutionService(config)
            result = service.run(progress_callback=update_progress)
        except Exception as exc:
            st.error(f"Falha na execução: {exc}")
        else:
            with results_container:
                st.success(result.message)
                st.write(f"Canais processados: {result.total_channels}")
                st.write(f"Vídeos extraídos: {result.total_videos}")
                st.write(f"JSON: {result.json_path}")
                if result.report_path:
                    st.write(f"Relatório: {result.report_path}")
                if (
                    mode == "full"
                    and result.report_path
                    and Path(result.report_path).suffix.lower() == ".txt"
                ):
                    report_path = Path(result.report_path)
                    if report_path.exists():
                        try:
                            report_text = report_path.read_text(encoding="utf-8")
                        except Exception as exc:
                            st.warning(f"Não foi possível carregar o relatório TXT: {exc}")
                        else:
                            st.subheader("Conteúdo do relatório (TXT)")
                            line_count = len(report_text.splitlines()) or 1
                            dynamic_height = min(900, max(200, line_count * 24))
                            st.text_area(
                                "Relatório TXT",
                                report_text,
                                height=dynamic_height,
                                disabled=True,
                            )
                st.write(f"Log: {result.log_path}")
                if result.token_details:
                    st.subheader("Tokens por vídeo")
                    ordered = sorted(result.token_details, key=lambda item: item["canal"])
                    st.dataframe(ordered, hide_index=True)
                total_prompt = result.total_prompt_tokens
                total_completion = result.total_completion_tokens
                total_tokens = total_prompt + total_completion
                st.metric(
                    "Total geral de tokens",
                    value=f"{total_tokens}",
                    delta=f"Entrada: {total_prompt} · Saída: {total_completion}",
                )
