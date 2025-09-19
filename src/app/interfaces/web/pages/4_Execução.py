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
from app.domain.youtube.groups import (
    YOUTUBE_CHANNEL_GROUP_OPTIONS,
    split_channel_groups,
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


def _analysis_method_label(source: str | None) -> str:
    mapping = {
        "transcricao_youtube": "Transcrição do vídeo (YouTube)",
        "asr_openai": "ASR via OpenAI (áudio baixado)",
        "asr_faster_whisper": "ASR via faster-whisper (áudio baixado)",
        "sem_transcricao": "Transcrição indisponível",
        "modo_simples": "Modo simple (sem transcrição)",
    }
    if not source:
        return "Não informado"
    return mapping.get(source, source)


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
    channel_options: dict[str, str] = {}
    channel_groups_map: dict[str, set[str]] = {}
    for item in channels_data:
        label = f"{item['foyt_nome_canal']} ({item['foyt_id_canal']})"
        channel_options[label] = item["foyt_id_canal"]
        channel_groups_map[label] = set(
            split_channel_groups(item.get("foyt_grupo_canal", ""))
        )
    llm_models = [model for model in list_llm_models() if model["status"]]
    llm_options = {
        f"{model['provedor']} - {model['modelo']}": model for model in llm_models
    }
    if not llm_options:
        st.warning(
            "Nenhum modelo LLM ativo encontrado. Cadastre um modelo antes de executar a pesquisa."
        )
    st.session_state.setdefault("youtube_group_filter", [])
    st.session_state.setdefault("youtube_auto_channels", [])
    st.session_state.setdefault("youtube_manual_channels", [])
    st.session_state.setdefault("youtube_selected_channels", [])

    def _apply_group_filter() -> None:
        selected_groups = set(st.session_state.get("youtube_group_filter", []))
        if not selected_groups:
            auto_labels: list[str] = []
        else:
            auto_labels = [
                label
                for label, groups in channel_groups_map.items()
                if groups and selected_groups.intersection(groups)
            ]
        sorted_auto = sorted(auto_labels)
        if st.session_state.youtube_auto_channels != sorted_auto:
            st.session_state.youtube_auto_channels = sorted_auto
        combined = sorted(
            set(st.session_state.youtube_auto_channels)
            | set(st.session_state.youtube_manual_channels)
        )
        st.session_state.youtube_selected_channels = combined

    with st.container():
        filter_col, _ = st.columns(2)
        with filter_col:
            st.multiselect(
                "Grupo(s) canal(is)",
                options=YOUTUBE_CHANNEL_GROUP_OPTIONS,
                key="youtube_group_filter",
                on_change=_apply_group_filter,
                help="Selecione um ou mais grupos para carregar automaticamente os canais vinculados.",
            )

    _apply_group_filter()

    with st.form("youtube_exec_form"):
        col1, col2 = st.columns(2)
        combined_selection = sorted(
            set(st.session_state.youtube_auto_channels)
            | set(st.session_state.youtube_manual_channels)
        )
        with col1:
            selected_widget = st.multiselect(
                "Canais cadastrados",
                options=list(channel_options.keys()),
                key="youtube_selected_channels",
            )
            auto_set = set(st.session_state.youtube_auto_channels)
            manual_selection = sorted(set(selected_widget) - auto_set)
            current_selection = sorted(set(selected_widget) | auto_set)
            manual_entries = st.text_area("Canais adicionais (um por linha)")
            days = st.number_input("Dias para filtrar", min_value=0, max_value=30, value=3)
            max_videos = st.number_input(
                "Limite de vídeos por canal", min_value=0, max_value=200, value=30
            )
        with col2:
            prefix = st.text_input("Prefixo dos arquivos", value="youtube_extraction")
            report_format = st.selectbox(
                "Formato do relatório", options=["txt", "json", "pdf", "html"], index=0
            )
            asr_provider = st.selectbox("Fornecedor de ASR", options=["faster-whisper", "openai"])
            no_asr = st.checkbox("Desativar ASR", value=False)
            llm_label = st.selectbox(
                "Modelo LLM",
                options=list(llm_options.keys()),
                disabled=not llm_options,
            )
            resumo_max = st.number_input(
                "Máximo de palavras no resumo",
                min_value=50,
                max_value=1000,
                value=settings.max_palavras_resumo,
                disabled=True,
                help="Altere este valor pelo menu de Configurações.",
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
    # Atualiza session_state apenas após submit
    if run_simple or run_full:
        st.session_state.youtube_manual_channels = manual_selection
        selected_labels = list(current_selection)
    else:
        selected_labels = list(current_selection)
    progress_container = st.container()
    results_container = st.container()
    if run_simple or run_full:
        mode = "simple" if run_simple else "full"
        channels: list[str] = [
            channel_options[label]
            for label in selected_labels
            if label in channel_options
        ]
        if manual_entries:
            channels.extend([line.strip() for line in manual_entries.splitlines() if line.strip()])
        if not selected_labels:
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
                translate_results=settings.translate_results,
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
                if result.channels_data:
                    st.subheader("Origem da análise por vídeo")
                    for channel_info in result.channels_data:
                        channel_name = channel_info.get("name") or channel_info.get(
                            "channel_id"
                        )
                        videos = channel_info.get("videos", [])
                        expander_label = f"{channel_name} — {len(videos)} vídeo(s)"
                        with st.expander(expander_label):
                            if not videos:
                                st.write("Nenhum vídeo analisado para este canal.")
                            else:
                                for video in videos:
                                    video_title = video.get("title") or "Vídeo sem título"
                                    video_url = video.get("url")
                                    method_label = _analysis_method_label(
                                        video.get("analysis_source")
                                    )
                                    if video_url:
                                        st.markdown(
                                            f"- [{video_title}]({video_url}) — {method_label}"
                                        )
                                    else:
                                        st.markdown(f"- {video_title} — {method_label}")
                if result.token_details:
                    st.subheader("Tokens por vídeo")
                    # Adiciona coluna de data do vídeo e origem do conteúdo
                    from datetime import datetime, timezone, timedelta
                    token_details = []
                    for item in result.token_details:
                        # Busca canal/vídeo na estrutura channels_data para pegar analysis_source e data
                        analysis_source = ""
                        data_video = ""
                        for channel in result.channels_data:
                            for video in channel.get("videos", []):
                                if video.get("id") == item.get("video_id"):
                                    analysis_source = video.get("analysis_source", "")
                                    data_raw = video.get("date_published") or video.get("published") or video.get("published_relative") or ""
                                    # Tenta converter para datetime
                                    dt_fmt = None
                                    dt_obj = None
                                    if data_raw:
                                        # Tenta ISO
                                        try:
                                            dt_obj = datetime.fromisoformat(str(data_raw))
                                        except Exception:
                                            # Tenta formatos comuns
                                            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                                                try:
                                                    dt_obj = datetime.strptime(str(data_raw), fmt)
                                                    break
                                                except Exception:
                                                    continue
                                    if dt_obj:
                                        # Ajusta para horário de Brasília (UTC-3)
                                        if dt_obj.tzinfo is None:
                                            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                                        dt_brasilia = dt_obj.astimezone(timezone(timedelta(hours=-3)))
                                        data_video = dt_brasilia.strftime("%d/%m/%Y %H:%M")
                                    else:
                                        data_video = str(data_raw)
                                    break
                            if analysis_source or data_video:
                                break
                        if analysis_source == "transcricao_youtube":
                            origem_conteudo = "transcrição"
                        elif analysis_source.startswith("asr_"):
                            origem_conteudo = "áudio"
                        else:
                            origem_conteudo = "-"
                        item = dict(item)
                        item = {"data_video": data_video, **item}  # insere data como primeira coluna
                        item["origem_conteudo"] = origem_conteudo
                        token_details.append(item)
                    ordered = sorted(token_details, key=lambda item: item["canal"])
                    st.dataframe(ordered, hide_index=True)
                total_prompt = result.total_prompt_tokens
                total_completion = result.total_completion_tokens
                total_tokens = total_prompt + total_completion
                st.metric(
                    "Total geral de tokens",
                    value=f"{total_tokens}",
                    delta=f"Entrada: {total_prompt} · Saída: {total_completion}",
                )

                # Exibe tempos de análise por vídeo e total
                if hasattr(result, "channels_data"):
                    tempos_videos = []
                    tempo_total = None
                    for channel in result.channels_data:
                        for video in channel.get("videos", []):
                            tempo = video.get("analysis_time")
                            if tempo:
                                tempos_videos.append((video.get("title", ""), tempo))
                    if hasattr(result, "started_at") and hasattr(result, "run_id"):
                        from datetime import datetime
                        # Tenta buscar tempo final pelo log_path
                        import os
                        try:
                            if result.log_path and os.path.exists(result.log_path):
                                import time
                                tempo_final = os.path.getmtime(result.log_path)
                                tempo_total = tempo_final - result.started_at.timestamp()
                        except Exception:
                            tempo_total = None
                    st.subheader("Tempo de análise por vídeo")
                    for titulo, tempo in tempos_videos:
                        st.write(f"{titulo}: {tempo:.2f} segundos")
                    if tempo_total:
                        st.write(f"Tempo total de execução: {tempo_total:.2f} segundos")
