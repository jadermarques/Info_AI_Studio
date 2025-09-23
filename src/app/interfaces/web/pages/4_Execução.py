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

# Submenus da execução na barra lateral
submenu = st.sidebar.radio(
    "Execução",
    options=["YouTube", "Fontes Web"],
    index=0,
    key="exec_submenu",
    help="Escolha o módulo de execução."
)

# Submenu: Fontes Web (com abas e formulário)
if submenu == "Fontes Web":
    st.subheader("Fontes Web")
    tab_prompt, tab_fontes = st.tabs(["Consulta via prompt", "Consulta via fontes"])

    with tab_prompt:
        from datetime import date as _date
        from datetime import datetime, timedelta
        from app.domain.web_prompt_service import get_defaults as web_get_defaults
        from app.domain.web_prompt_execution import (
            WebPromptParams,
            execute_web_prompt,
            _build_prompt_text,
        )
        from app.domain.llm_service import list_llm_models as _list_llm

        defaults = web_get_defaults()
        st.markdown("Preencha os campos para realizar uma consulta baseada em prompt.")
        with st.form("web_sources_prompt_form"):
            col1, col2 = st.columns(2)
            with col1:
                dt_inicio = st.date_input(
                    "Data de início",
                    value=_date.today() - timedelta(days=1),
                    help="Data inicial do período (obrigatória, formato dd/mm/aaaa).",
                    key="web_dt_inicio",
                    format="DD/MM/YYYY",
                )
                persona = st.text_input(
                    "Persona",
                    value=defaults.persona,
                    help="Descreva quem irá analisar/produzir o conteúdo (obrigatório).",
                    key="web_persona",
                )
                publico_alvo = st.text_input(
                    "Público-alvo",
                    value=defaults.publico_alvo,
                    help="Defina para quem o conteúdo se destina (obrigatório).",
                    key="web_publico_alvo",
                )
            with col2:
                dt_fim = st.date_input(
                    "Data de término",
                    value=_date.today(),
                    help="Data final do período (obrigatória, formato dd/mm/aaaa).",
                    key="web_dt_fim",
                    format="DD/MM/YYYY",
                )
                formato_saida = st.selectbox(
                    "Formato de saída",
                    options=[".txt", ".md", ".pdf", ".json", ".xml"],
                    index=0,
                    help="Selecione o formato do relatório (obrigatório).",
                    key="web_formato_saida",
                )
                segmentos = st.text_input(
                    "Segmentos",
                    value=defaults.segmentos,
                    help="Liste os segmentos a considerar (obrigatório).",
                    key="web_segmentos",
                )
            # Usar instruções padrão (sem campo na interface)
            instrucoes = defaults.instrucoes
            # Botão para preencher o campo de prompt com os valores atuais
            atualizar_clicked = st.form_submit_button(
                "Atualizar prompt de consulta",
                use_container_width=True,
            )
            if atualizar_clicked:
                try:
                    settings = get_settings()
                    base_prompt = (
                        st.session_state.get("web_prompt_consulta")
                        or (defaults.prompt or "")
                    )
                    preview_params = WebPromptParams(
                        data_inicio=dt_inicio,
                        data_fim=dt_fim,
                        persona=persona.strip(),
                        publico_alvo=publico_alvo.strip(),
                        segmentos=segmentos.strip(),
                        instrucoes=(instrucoes or "").strip(),
                        prompt_base=base_prompt,
                        formato_saida=formato_saida,
                        llm_provedor="",
                        llm_modelo="",
                        api_key="",
                        outdir=settings.resultados_dir,
                    )
                    final_prompt_text = _build_prompt_text(preview_params)
                    st.session_state["web_prompt_consulta"] = final_prompt_text
                    st.success("Prompt atualizado com os valores preenchidos.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível atualizar o prompt: {exc}")
            prompt_consulta = st.text_area(
                "Prompt da consulta",
                value=(defaults.prompt or ""),
                help="Texto que será enviado ao LLM (obrigatório para execução).",
                key="web_prompt_consulta",
                height=240,
            )
            # Seleção de modelo LLM (obrigatório)
            llm_models = [m for m in _list_llm() if m.get("status")]
            llm_options = {f"{m['provedor']} - {m['modelo']}": m for m in llm_models}
            llm_label = st.selectbox(
                "Modelo LLM",
                options=list(llm_options.keys()) or ["—"],
                index=0 if llm_options else 0,
                disabled=not llm_options,
                help="Selecione o modelo LLM cadastrado para executar o prompt.",
            )

            # Aviso de dependência para PDF (padrão reaproveitado)
            try:
                import fpdf  # type: ignore  # noqa: F401
                _pdf_ok_web = True
            except Exception:
                _pdf_ok_web = False
            if formato_saida == ".pdf" and not _pdf_ok_web:
                st.warning("Para gerar PDF, instale a biblioteca 'fpdf2' (pip install fpdf2).", icon="ℹ️")

            submitted = st.form_submit_button("Executar prompt", use_container_width=True, disabled=not llm_options)

        if submitted:
            erros: list[str] = []
            if not dt_inicio:
                erros.append("Informe a data de início.")
            if not dt_fim:
                erros.append("Informe a data de término.")
            try:
                if dt_inicio and dt_fim and dt_inicio > dt_fim:
                    erros.append("A data de término deve ser maior ou igual à data de início.")
            except Exception:
                pass
            if not persona.strip():
                erros.append("Informe a persona.")
            if not publico_alvo.strip():
                erros.append("Informe o público-alvo.")
            if not segmentos.strip():
                erros.append("Informe os segmentos.")
            if not prompt_consulta.strip():
                erros.append("Informe o prompt da consulta.")
            selected_model = llm_options.get(llm_label) if llm_options else None
            if not selected_model:
                erros.append("Selecione um modelo LLM válido.")
            elif not selected_model.get("api_key"):
                erros.append("O modelo LLM selecionado não possui uma chave de API válida.")
            if erros:
                for e in erros:
                    st.error(e)
                st.stop()

            # Execução do prompt com progresso
            progress = st.progress(0)
            status = st.empty()
            status.write("Preparando execução...")
            progress.progress(5)

            try:
                settings = get_settings()
                params = WebPromptParams(
                    data_inicio=dt_inicio,
                    data_fim=dt_fim,
                    persona=persona,
                    publico_alvo=publico_alvo,
                    segmentos=segmentos,
                    instrucoes=instrucoes,
                    prompt_base=prompt_consulta,
                    formato_saida=formato_saida,
                    llm_provedor=selected_model.get("provedor"),
                    llm_modelo=selected_model.get("modelo"),
                    api_key=selected_model.get("api_key"),
                    outdir=settings.resultados_dir,
                )
                status.write("Chamando o provedor LLM...")
                progress.progress(25)
                result = execute_web_prompt(params)
                progress.progress(90)
            except Exception as exc:
                st.error(f"Falha ao executar o prompt: {exc}")
            else:
                progress.progress(100)
                st.success("Execução concluída.")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"Data/hora início execução: {result.started_at.strftime('%d/%m/%Y %H:%M:%S')}")
                    st.write(f"Data/hora término execução: {result.ended_at.strftime('%d/%m/%Y %H:%M:%S')}")
                    st.write(f"Tempo total da execução: {result.elapsed_seconds:.2f} s")
                    st.write(f"Modelo LLM utilizado: {result.model_used}")
                    st.write(f"Total de tokens enviados: {result.prompt_tokens}")
                with col_b:
                    st.write(f"Total de tokens recebidos: {result.completion_tokens}")
                    st.write(f"Custo estimado da consulta: R$ {result.cost_estimated:.4f}")
                    if result.report_path:
                        rp = Path(result.report_path)
                        if rp.exists():
                            st.write(f"Relatório gerado: {rp}")
                            mime_map = {
                                ".xml": "application/xml",
                                ".json": "application/json",
                                ".txt": "text/plain; charset=utf-8",
                                ".md": "text/markdown; charset=utf-8",
                                ".html": "text/html; charset=utf-8",
                                ".pdf": "application/pdf",
                            }
                            ext = rp.suffix.lower()
                            mime = mime_map.get(ext, "application/octet-stream")
                            try:
                                data = rp.read_bytes()
                                st.download_button(
                                    label=f"Baixar saída ({ext[1:]})",
                                    data=data,
                                    file_name=rp.name,
                                    mime=mime,
                                )
                            except Exception:
                                pass
                with st.expander("Prompt executado", expanded=False):
                    st.code(result.prompt_executed, language="markdown")
                with st.expander("Resultado do prompt", expanded=True):
                    # Renderização simples conforme formato selecionado
                    if formato_saida in (".md", "md"):
                        st.markdown(result.result_text)
                    elif formato_saida in (".json", "json"):
                        try:
                            obj = __import__("json").loads(result.result_text)
                            st.code(__import__("json").dumps(obj, ensure_ascii=False, indent=2), language="json")
                        except Exception:
                            st.text(result.result_text)
                    elif formato_saida in (".xml", "xml"):
                        st.code(result.result_text, language="xml")
                    else:
                        st.text(result.result_text)
                if result.log_path:
                    lp = Path(result.log_path)
                    if lp.exists():
                        try:
                            st.markdown(f"[🔗 Abrir log]({lp.resolve().as_uri()})")
                        except Exception:
                            # Fallback: oferecer download direto
                            try:
                                st.download_button(
                                    label="Baixar log (.log)",
                                    data=lp.read_bytes(),
                                    file_name=lp.name,
                                    mime="text/plain; charset=utf-8",
                                )
                            except Exception:
                                st.write(f"Log disponível em: {lp}")

    with tab_fontes:
        st.info("Consulta via fontes: especificação será definida posteriormente. Aba criada como placeholder.")
        st.caption("Quando definido, esta aba permitirá selecionar fontes específicas (sites/blogs) para consulta.")

    st.stop()

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
        """Atualiza apenas a lista automática para visualização; não altera a seleção manual.
        A seleção efetiva por grupos será calculada no momento da execução.
        """
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

    with st.container():
        filter_col, _ = st.columns(2)
        with filter_col:
            st.multiselect(
                "Grupo(s) canal(is)",
                options=YOUTUBE_CHANNEL_GROUP_OPTIONS,
                key="youtube_group_filter",
                on_change=_apply_group_filter,
                help=(
                    "Escolha um ou mais grupos OU escolha canais cadastrados ao lado. "
                    "Quando grupos forem selecionados, a seleção de canais será desabilitada."
                ),
                disabled=bool(st.session_state.get("youtube_selected_channels")),
            )

    # Importante: não chamar aqui para evitar sobrescrever seleção ao submeter o formulário

    # Shared selection controls (outside tabs) to keep state consistent
    with st.container():
        col_left, col_right = st.columns(2)
        with col_left:
            selected_widget = st.multiselect(
                "Canais cadastrados",
                options=list(channel_options.keys()),
                key="youtube_selected_channels",
                disabled=bool(st.session_state.get("youtube_group_filter")),
            )
            manual_entries = st.text_area(
                "Canais adicionais (um por linha)",
                key="youtube_manual_entries",
                disabled=True,
                help="Campo desabilitado. Use grupos OU canais cadastrados."
            )
        with col_right:
            days = st.number_input("Dias para filtrar", min_value=0, max_value=30, value=3, key="youtube_days")
            max_videos = st.number_input(
                "Limite de vídeos por canal", min_value=0, max_value=200, value=30, key="youtube_max_videos"
            )

    # Tabs: Simple and Full (each with its own form for execution options)
    guia_simples, guia_completo = st.tabs(["Modo simples", "Modo completo"])

    def _exec_form(key_prefix: str, default_prefix: str, mode_label: str):
        with st.form(f"youtube_exec_form_{key_prefix}"):
            # Campos alinhados à esquerda dentro do formulário
            prefix = st.text_input("Prefixo dos arquivos", value=default_prefix, key=f"prefix_{key_prefix}")
            report_format = st.radio(
                "Formato do relatório",
                options=["txt", "md", "json", "pdf", "html", "xml"],
                index=0,
                horizontal=True,
                help="Escolha apenas um formato. 'md' gera Markdown.",
                key=f"report_format_{key_prefix}",
            )
            if key_prefix != "simple":
                asr_provider = st.selectbox(
                    "Fornecedor de ASR",
                    options=["faster-whisper", "openai"],
                    key=f"asr_provider_{key_prefix}",
                )
                no_asr = st.checkbox(
                    "Desativar ASR",
                    value=False,
                    key=f"no_asr_{key_prefix}",
                )
            else:
                # Modo simples: ocultar controles de ASR e usar padrões
                asr_provider = "faster-whisper"
                no_asr = False
            llm_label = st.selectbox(
                "Modelo LLM",
                options=list(llm_options.keys()),
                disabled=not llm_options,
                key=f"llm_label_{key_prefix}",
            )
            # legenda removida conforme solicitado
            run_btn = st.form_submit_button(
                f"Executar {mode_label}", use_container_width=True, disabled=not llm_options
            )
        return run_btn, prefix, report_format, asr_provider, no_asr, llm_label

    with guia_simples:
        run_simple, prefix, report_format, asr_provider, no_asr, llm_label = _exec_form(
            key_prefix="simple", default_prefix="youtube_extract_simple", mode_label="modo simples"
        )
        # Aviso se PDF foi selecionado e dependência não estiver instalada
        try:
            import fpdf  # type: ignore
            _pdf_ok_simple = True
        except Exception:
            _pdf_ok_simple = False
        if report_format == "pdf" and not _pdf_ok_simple:
            st.warning("Para gerar PDF, instale a biblioteca 'fpdf2' (pip install fpdf2).", icon="ℹ️")
    with guia_completo:
        # Opção específica do modo completo: traduzir títulos
        st.checkbox(
            "Traduzir títulos para PT-BR",
            key="youtube_full_translate_titles",
            help="Quando ligado, os títulos serão traduzidos para Português (Brasil) usando o LLM."
        )
        run_full, prefix_full, report_format_full, asr_provider_full, no_asr_full, llm_label_full = _exec_form(
            key_prefix="full", default_prefix="youtube_extract_full", mode_label="modo completo"
        )
        # Aviso se PDF foi selecionado e dependência não estiver instalada
        try:
            import fpdf  # type: ignore
            _pdf_ok_full = True
        except Exception:
            _pdf_ok_full = False
        if report_format_full == "pdf" and not _pdf_ok_full:
            st.warning("Para gerar PDF, instale a biblioteca 'fpdf2' (pip install fpdf2).", icon="ℹ️")
    # Atualiza session_state apenas após submit
    # Decide qual guia acionou
    triggered = None
    if run_simple:
        triggered = "simple"
        selected_labels = list(selected_widget)
        manual_entries_v = st.session_state.get("youtube_manual_entries", "")
        days_v = int(st.session_state.get("youtube_days", 3) or 3)
        max_videos_v = int(st.session_state.get("youtube_max_videos", 30) or 30)
        prefix_v = prefix
        report_format_v = report_format
        asr_provider_v = asr_provider
        no_asr_v = no_asr
        llm_label_v = llm_label
    elif run_full:
        triggered = "full"
        selected_labels = list(selected_widget)
        manual_entries_v = st.session_state.get("youtube_manual_entries", "")
        days_v = int(st.session_state.get("youtube_days", 3) or 3)
        max_videos_v = int(st.session_state.get("youtube_max_videos", 30) or 30)
        prefix_v = prefix_full
        report_format_v = report_format_full
        asr_provider_v = asr_provider_full
        no_asr_v = no_asr_full
        llm_label_v = llm_label_full
    else:
        selected_labels = list(st.session_state.get("youtube_selected_channels", []))
        manual_entries_v = ""
        days_v = 3
        max_videos_v = 30
        prefix_v = "youtube_extract_simple"
        report_format_v = "txt"
        asr_provider_v = "faster-whisper"
        no_asr_v = False
        llm_label_v = ""
    progress_container = st.container()
    results_container = st.container()
    if run_simple or run_full:
        mode = "simple" if triggered == "simple" else "full"
        # Determina canais conforme regra: se grupos selecionados, usar TODOS os canais dos grupos;
        # caso contrário, usar os canais cadastrados selecionados.
        selected_groups_exec = set(st.session_state.get("youtube_group_filter", []))
        if selected_groups_exec:
            channels: list[str] = [
                channel_options[label]
                for label, groups in channel_groups_map.items()
                if groups and selected_groups_exec.intersection(groups)
            ]
            # remove duplicados preservando ordem
            seen = set()
            channels = [c for c in channels if not (c in seen or seen.add(c))]
        else:
            channels = [
                channel_options[label]
                for label in selected_labels
                if label in channel_options
            ]
        # Validação: deve haver ao menos um grupo selecionado OU um canal selecionado
        if not selected_groups_exec and not channels:
            st.error("Selecione um ou mais grupos de canais OU um ou mais canais cadastrados.")
            st.stop()
        # Se grupos foram selecionados mas não há canais vinculados, interrompe
        if selected_groups_exec and not channels:
            st.error("Nenhum canal encontrado nos grupos de canais selecionados.")
            st.stop()
        if not llm_label_v:
            st.error("Selecione um modelo LLM para continuar.")
            st.stop()
        selected_model = llm_options.get(llm_label_v)
        if not selected_model or not selected_model.get("api_key"):
            st.error("O modelo LLM selecionado não possui uma chave de API válida.")
            st.stop()
        progress_messages: list[str] = []
        progress_placeholder = progress_container.empty()
        total_channels_exec = len(channels)

        def update_progress(message: str) -> None:
            # Atualiza log textual
            progress_messages.append(message)
            formatted = "\n".join(f"- {msg}" for msg in progress_messages)
            progress_placeholder.markdown(formatted or "- Aguardando início da execução...")
            # Tenta atualizar barra de progresso conforme canal atual
            try:
                import re
                # Por canal
                m = re.search(r"Processando canal\s+(\d+)/(\d+)", message)
                if m:
                    idx = int(m.group(1))
                    tot = int(m.group(2)) or total_channels_exec or 1
                    percent = max(0, min(100, int(idx * 100 / tot)))
                    progress_bar.progress(percent)
                    try:
                        progress_caption.caption(f"Canal {idx}/{tot}")
                    except Exception:
                        pass
                # Por vídeo dentro do canal
                # Captura opcional do título após dois-pontos
                mv = re.search(r"Processando vídeo\s+(\d+)/(\d+) do canal\s+(\d+)/(\d+)(?::\s*(.*))?", message)
                if mv:
                    vid_i = int(mv.group(1))
                    vid_tot = max(1, int(mv.group(2)))
                    ch_i = int(mv.group(3))
                    ch_tot = max(1, int(mv.group(4)))
                    titulo = (mv.group(5) or "").strip()
                    if titulo:
                        # Trunca título para não quebrar layout
                        max_len = 80
                        if len(titulo) > max_len:
                            titulo = titulo[:max_len - 1].rstrip() + "…"
                    # Progresso composto: progresso por canal + fração do canal atual
                    base = (ch_i - 1) / ch_tot
                    frac_canal = (vid_i / vid_tot) / ch_tot
                    percent = int((base + frac_canal) * 100)
                    percent = max(0, min(100, percent))
                    progress_bar.progress(percent)
                    try:
                        caption_txt = f"Canal {ch_i}/{ch_tot} — Vídeo {vid_i}/{vid_tot}"
                        if titulo:
                            caption_txt += f" — {titulo}"
                        progress_caption.caption(caption_txt)
                    except Exception:
                        pass
                elif "Iniciando processamento" in message:
                    progress_bar.progress(1)
            except Exception:
                pass

        update_progress("Preparando execução...")
        try:
            config = YouTubeExtractionConfig(
                outdir=(settings.resultados_dir).resolve(),
                prefix=prefix_v,
                days=int(days_v) if days_v else None,
                channels=channels,
                channels_file=None,
                mode=mode,
                no_llm=False,
                asr_enabled=not no_asr_v,
                asr_provider=asr_provider_v,
                llm_provider=selected_model.get("provedor"),
                llm_model=selected_model.get("modelo", settings.llm_model),
                llm_key=selected_model.get("api_key"),
                resumo_max_palavras=int(settings.max_palavras_resumo),
                cookies=settings.cookies_path,
                user_agent=settings.user_agent,
                report_format=report_format_v,
                max_videos=int(max_videos_v) if max_videos_v else None,
                translate_results=settings.translate_results,
                ui_extras={
                    "selected_groups": list(st.session_state.get("youtube_group_filter", [])),
                    "selected_channel_labels": list(selected_labels),
                    "manual_entries": manual_entries_v,
                    "translate_titles": bool(st.session_state.get("youtube_full_translate_titles", False)),
                },
            )
            service = YouTubeExecutionService(config)
            # Mostra parâmetros selecionados ANTES de iniciar
            with results_container:
                st.subheader(f"Iniciando execução modo {mode.upper()}")
                st.markdown("**Valores selecionados**")
                st.write(f"Grupos de canais selecionados: {', '.join(st.session_state.get('youtube_group_filter', [])) or '—'}")
                st.write(f"Canais cadastrados: {len([l for l in selected_labels if l in channel_options])}")
                st.write(f"Canais adicionais: {manual_entries_v or '—'}")
                st.write(f"Dias para filtrar: {days_v}")
                st.write(f"Limite de vídeos por canal: {max_videos_v}")
                st.write(f"Prefixo dos arquivos: {prefix_v}")
                st.write(f"Formato do relatório: {report_format_v}")
                # Exibe ASR apenas quando não for modo simples
                if prefix_v != "youtube_extract_simple":
                    st.write(f"Fornecedor de ASR: {asr_provider_v}")
                    st.write(f"Desativar ASR (sim ou não): {'sim' if no_asr_v else 'não'}")
                st.write(f"Modelo LLM: {llm_label_v}")
                st.divider()
                st.markdown("**Canais**")
                st.write(f"Canais selecionados para análise: {len(channels)}")
                progress_caption = st.empty()
                progress_bar = st.progress(0)
            # Executa serviço
            result = service.run(progress_callback=update_progress)
        except Exception as exc:
            st.error(f"Falha na execução: {exc}")
        else:
            with results_container:
                st.success(result.message)
                st.write(f"Canais processados: {result.total_channels}")
                st.write(f"Vídeos extraídos: {result.total_videos}")
                # Linha JSON: caminho à esquerda, links à direita
                json_col_left, json_col_right = st.columns([3, 2])
                with json_col_left:
                    st.write(f"JSON: {result.json_path}")
                with json_col_right:
                    try:
                        if result.json_path:
                            jp = Path(result.json_path)
                            if jp.exists():
                                st.markdown(
                                    f"[🔗 Abrir arquivo]({jp.as_uri()}) · [📁 Abrir pasta]({jp.parent.as_uri()})"
                                )
                    except Exception:
                        pass
                if result.report_path:
                    rep_col_left, rep_col_right = st.columns([3, 2])
                    with rep_col_left:
                        rp = Path(result.report_path)
                        size_txt = ""
                        try:
                            if rp.exists():
                                size = rp.stat().st_size
                                # tamanho humano
                                for unit in ["B","KB","MB","GB"]:
                                    if size < 1024.0:
                                        size_txt = f" ({size:.1f} {unit})" if unit != "B" else f" ({int(size)} {unit})"
                                        break
                                    size /= 1024.0
                        except Exception:
                            pass
                        st.write(f"Relatório: {result.report_path}{size_txt}")
                    with rep_col_right:
                        try:
                            if rp.exists():
                                file_uri = rp.as_uri()
                                dir_uri = rp.parent.as_uri()
                                st.markdown(
                                    f"[🔗 Abrir arquivo]({file_uri}) · [📁 Abrir pasta]({dir_uri})"
                                )
                                # Botão de download
                                mime_map = {
                                    ".xml": "application/xml",
                                    ".json": "application/json",
                                    ".txt": "text/plain; charset=utf-8",
                                    ".md": "text/markdown; charset=utf-8",
                                    ".html": "text/html; charset=utf-8",
                                    ".pdf": "application/pdf",
                                }
                                ext = rp.suffix.lower()
                                mime = mime_map.get(ext, "application/octet-stream")
                                try:
                                    data = rp.read_bytes()
                                    st.download_button(
                                        label=f"Baixar relatório ({ext[1:]})",
                                        data=data,
                                        file_name=rp.name,
                                        mime=mime,
                                    )
                                except Exception:
                                    pass
                        except Exception:
                            pass
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
                            if report_text.strip():
                                with st.expander("Conteúdo do relatório (TXT)", expanded=False):
                                    line_count = len(report_text.splitlines()) or 1
                                    dynamic_height = min(600, max(240, line_count * 18))
                                    st.text_area(
                                        "Relatório TXT",
                                        report_text,
                                        height=dynamic_height,
                                        disabled=True,
                                    )
                            else:
                                st.info("Relatório vazio (TXT)")
                # Prévia de relatório Markdown quando gerado
                if result.report_path and Path(result.report_path).suffix.lower() == ".md":
                    report_path = Path(result.report_path)
                    if report_path.exists():
                        try:
                            md_text = report_path.read_text(encoding="utf-8")
                        except Exception as exc:
                            st.warning(f"Não foi possível carregar o relatório MD: {exc}")
                        else:
                            if md_text.strip():
                                with st.expander("Conteúdo do relatório (Markdown)", expanded=False):
                                    st.markdown(md_text)
                            else:
                                st.info("Relatório vazio (Markdown)")
                # Prévia de relatório JSON quando gerado
                if result.report_path and Path(result.report_path).suffix.lower() == ".json":
                    report_path = Path(result.report_path)
                    if report_path.exists():
                        try:
                            import json as _json
                            raw = report_path.read_text(encoding="utf-8")
                            obj = _json.loads(raw)
                            pretty = _json.dumps(obj, ensure_ascii=False, indent=2)
                        except Exception as exc:
                            st.warning(f"Não foi possível carregar o relatório JSON: {exc}")
                        else:
                            if pretty.strip():
                                with st.expander("Conteúdo do relatório (JSON)", expanded=False):
                                    st.code(pretty, language="json")
                            else:
                                st.info("Relatório vazio (JSON)")
                # Prévia de relatório HTML quando gerado
                if result.report_path and Path(result.report_path).suffix.lower() == ".html":
                    report_path = Path(result.report_path)
                    if report_path.exists():
                        try:
                            html_text = report_path.read_text(encoding="utf-8")
                        except Exception as exc:
                            st.warning(f"Não foi possível carregar o relatório HTML: {exc}")
                        else:
                            if html_text.strip():
                                with st.expander("Conteúdo do relatório (HTML)", expanded=False):
                                    st.code(html_text, language="html")
                            else:
                                st.info("Relatório vazio (HTML)")
                # Prévia de relatório XML quando gerado
                if result.report_path and Path(result.report_path).suffix.lower() == ".xml":
                    report_path = Path(result.report_path)
                    if report_path.exists():
                        try:
                            xml_text = report_path.read_text(encoding="utf-8")
                        except Exception as exc:
                            st.warning(f"Não foi possível carregar o relatório XML: {exc}")
                        else:
                            if xml_text.strip():
                                with st.expander("Conteúdo do relatório (XML)", expanded=False):
                                    # Exibe com syntax highlight
                                    st.code(xml_text, language="xml")
                            else:
                                st.info("Relatório vazio (XML)")
                log_col_left, log_col_right = st.columns([3, 2])
                with log_col_left:
                    st.write(f"Log: {result.log_path}")
                with log_col_right:
                    try:
                        if result.log_path:
                            lp = Path(result.log_path)
                            if lp.exists():
                                st.markdown(
                                    f"[🔗 Abrir arquivo]({lp.as_uri()}) · [📁 Abrir pasta]({lp.parent.as_uri()})"
                                )
                    except Exception:
                        pass
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
                # Resumo Extração (somente Modo completo)
                if mode == "full" and result.channels_data:
                    st.subheader("Resumo Extração")
                    from datetime import datetime, timezone, timedelta
                    import io, csv
                    rows_resumo: list[dict] = []
                    for channel in result.channels_data:
                        canal_nome = channel.get("name") or channel.get("channel_id")
                        for v in channel.get("videos", []):
                            # Data/hora do vídeo em horário de Brasília
                            data_raw = v.get("date_published") or v.get("published") or v.get("published_relative") or ""
                            dt_obj = None
                            if data_raw:
                                try:
                                    dt_obj = datetime.fromisoformat(str(data_raw))
                                except Exception:
                                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                                        try:
                                            dt_obj = datetime.strptime(str(data_raw), fmt)
                                            break
                                        except Exception:
                                            continue
                            if dt_obj:
                                if dt_obj.tzinfo is None:
                                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                                dt_brasilia = dt_obj.astimezone(timezone(timedelta(hours=-3)))
                                data_fmt = dt_brasilia.strftime("%d/%m/%Y %H:%M")
                            else:
                                data_fmt = str(data_raw)
                            # Origem do conteúdo
                            analysis_source = v.get("analysis_source", "") or ""
                            if analysis_source == "transcricao_youtube":
                                origem_conteudo = "transcrição"
                            elif str(analysis_source).startswith("asr_"):
                                origem_conteudo = "áudio"
                            else:
                                origem_conteudo = "-"
                            # Resumo/LLM
                            summary = v.get("summary") or {}
                            palavras_chave = summary.get("palavras_chave") or []
                            if isinstance(palavras_chave, str):
                                palavras_chave = [p.strip() for p in palavras_chave.split(",") if p.strip()]
                            resumo_topicos = (summary.get("resumo_em_topicos") or "").strip()
                            # Modelo
                            modelo_llm = summary.get("model") or (selected_model.get("modelo") if 'selected_model' in locals() and selected_model else "")
                            # Título pt: placeholder igual ao original se não houver campo dedicado
                            titulo_original = v.get("title", "")
                            titulo_pt = v.get("title_pt") or titulo_original
                            titulo_traduzido = "sim" if (titulo_pt and titulo_pt != titulo_original) else "não"
                            # Tempo de análise em minutos
                            analise_seg = v.get("analysis_time") or 0
                            try:
                                analise_min = round(float(analise_seg) / 60.0, 2)
                            except Exception:
                                analise_min = 0.0
                            # Tokens
                            tokens_in = summary.get("prompt_tokens", 0) or 0
                            tokens_out = summary.get("completion_tokens", 0) or 0
                            rows_resumo.append({
                                "data hora postagem video": data_fmt,
                                "nome do canal": canal_nome,
                                "titulo do video (lingua original)": titulo_original,
                                "titulo do video (em portugues)": titulo_pt,
                                "titulo foi traduzido": titulo_traduzido,
                                "modelo LLM usado": modelo_llm,
                                "resumo do video (1 frase)": summary.get("resumo_uma_frase", ""),
                                "resumo": summary.get("resumo", ""),
                                "palavras-chave": ", ".join(palavras_chave),
                                "resumo em tópicos": resumo_topicos,
                                "duracao do video": v.get("duration", ""),
                                "origem do conteudo": origem_conteudo,
                                "possui transcricao": "sim" if v.get("has_transcript") else "não",
                                "url do video": v.get("url", ""),
                                "tempo total de analise do video em minutos": analise_min,
                                "tokens enviados": tokens_in,
                                "tokens recebidos": tokens_out,
                            })
                    if rows_resumo:
                        st.dataframe(rows_resumo, hide_index=True)
                        # Exportar CSV
                        csv_buffer = io.StringIO()
                        fieldnames = list(rows_resumo[0].keys())
                        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
                        writer.writeheader()
                        for r in rows_resumo:
                            writer.writerow(r)
                        st.download_button(
                            label="Exportar CSV",
                            data=csv_buffer.getvalue().encode("utf-8"),
                            file_name="resumo_extracao.csv",
                            mime="text/csv",
                        )
                # Modo simple: montar tabela de vídeos encontrados com campos solicitados
                if mode == "simple" and result.channels_data:
                    st.subheader("Vídeos encontrados")
                    rows = []
                    from datetime import datetime, timezone, timedelta
                    for channel in result.channels_data:
                        canal_nome = channel.get("name") or channel.get("channel_id")
                        for v in channel.get("videos", []):
                            # data do vídeo: converter para Brasília
                            data_raw = v.get("date_published") or v.get("published")
                            dt_fmt = None
                            dt_obj = None
                            if data_raw:
                                try:
                                    dt_obj = datetime.fromisoformat(str(data_raw))
                                except Exception:
                                    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                                        try:
                                            dt_obj = datetime.strptime(str(data_raw), fmt)
                                            break
                                        except Exception:
                                            continue
                            if dt_obj:
                                if dt_obj.tzinfo is None:
                                    dt_obj = dt_obj.replace(tzinfo=timezone.utc)
                                dt_brasilia = dt_obj.astimezone(timezone(timedelta(hours=-3)))
                                data_fmt = dt_brasilia.strftime("%d/%m/%y %H:%M")
                            else:
                                data_fmt = str(data_raw or "")
                            rows.append({
                                "data video": data_fmt,
                                "nome canal": canal_nome,
                                "titulo do video": v.get("title",""),
                                "id do video": v.get("id",""),
                                "link do video (url)": v.get("url",""),
                                "tamanho do video": v.get("duration",""),
                                "idioma original": v.get("language",""),
                                "tem transcricao": "sim" if v.get("has_transcript") else "não",
                                "visualizacoes": v.get("view_count", 0),
                            })
                    if rows:
                        st.dataframe(rows, hide_index=True)
                # Tokens
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
                # Atualiza barra de progresso para 100% ao final (somente tela)
                try:
                    progress_bar.progress(100)
                except Exception:
                    pass
