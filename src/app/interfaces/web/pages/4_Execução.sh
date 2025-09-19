 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/src/app/interfaces/web/pages/4_Execução.py b/src/app/interfaces/web/pages/4_Execução.py
index 48b93bee61bb63631d81ad36483beaf20eeef9b3..5d378340a6f824b7957cbde639f7871ce7672bba 100644
--- a/src/app/interfaces/web/pages/4_Execução.py
+++ b/src/app/interfaces/web/pages/4_Execução.py
@@ -1,111 +1,197 @@
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
+from app.domain.youtube.groups import (
+    YOUTUBE_CHANNEL_GROUP_OPTIONS,
+    split_channel_groups,
+)
 
 DEFAULT_USER_AGENT = (
     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
 )
 
+
+def _analysis_method_label(source: str | None) -> str:
+    mapping = {
+        "transcricao_youtube": "Transcrição do vídeo (YouTube)",
+        "asr_openai": "ASR via OpenAI (áudio baixado)",
+        "asr_faster_whisper": "ASR via faster-whisper (áudio baixado)",
+        "sem_transcricao": "Transcrição indisponível",
+        "modo_simples": "Modo simple (sem transcrição)",
+    }
+    if not source:
+        return "Não informado"
+    return mapping.get(source, source)
+
+
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
-    options = {
-        f"{item['foyt_nome_canal']} ({item['foyt_id_canal']})": item["foyt_id_canal"]
-        for item in channels_data
-    }
+    channel_options: dict[str, str] = {}
+    channel_groups_map: dict[str, set[str]] = {}
+    for item in channels_data:
+        label = f"{item['foyt_nome_canal']} ({item['foyt_id_canal']})"
+        channel_options[label] = item["foyt_id_canal"]
+        channel_groups_map[label] = set(
+            split_channel_groups(item.get("foyt_grupo_canal", ""))
+        )
     llm_models = [model for model in list_llm_models() if model["status"]]
     llm_options = {
         f"{model['provedor']} - {model['modelo']}": model for model in llm_models
     }
     if not llm_options:
         st.warning(
             "Nenhum modelo LLM ativo encontrado. Cadastre um modelo antes de executar a pesquisa."
         )
+    st.session_state.setdefault("youtube_group_filter", [])
+    st.session_state.setdefault("youtube_auto_channels", [])
+    st.session_state.setdefault("youtube_manual_channels", [])
+    st.session_state.setdefault("youtube_selected_channels", [])
+
+    def _apply_group_filter() -> None:
+        selected_groups = set(st.session_state.get("youtube_group_filter", []))
+        if not selected_groups:
+            auto_labels: list[str] = []
+        else:
+            auto_labels = [
+                label
+                for label, groups in channel_groups_map.items()
+                if groups and selected_groups.intersection(groups)
+            ]
+        sorted_auto = sorted(auto_labels)
+        if st.session_state.youtube_auto_channels != sorted_auto:
+            st.session_state.youtube_auto_channels = sorted_auto
+        combined = sorted(
+            set(st.session_state.youtube_auto_channels)
+            | set(st.session_state.youtube_manual_channels)
+        )
+        st.session_state.youtube_selected_channels = combined
+
+    with st.container():
+        filter_col, _ = st.columns(2)
+        with filter_col:
+            st.multiselect(
+                "Grupo(s) canal(is)",
+                options=YOUTUBE_CHANNEL_GROUP_OPTIONS,
+                key="youtube_group_filter",
+                on_change=_apply_group_filter,
+                help="Selecione um ou mais grupos para carregar automaticamente os canais vinculados.",
+            )
+
+    _apply_group_filter()
+
     with st.form("youtube_exec_form"):
         col1, col2 = st.columns(2)
+        combined_selection = sorted(
+            set(st.session_state.youtube_auto_channels)
+            | set(st.session_state.youtube_manual_channels)
+        )
+        st.session_state.youtube_selected_channels = combined_selection
         with col1:
-            selected = st.multiselect("Canais cadastrados", options=list(options.keys()))
+            selected_widget = st.multiselect(
+                "Canais cadastrados",
+                options=list(channel_options.keys()),
+                key="youtube_selected_channels",
+            )
+            auto_set = set(st.session_state.youtube_auto_channels)
+            st.session_state.youtube_manual_channels = sorted(set(selected_widget) - auto_set)
+            current_selection = sorted(set(selected_widget) | auto_set)
+            st.session_state.youtube_selected_channels = current_selection
             manual_entries = st.text_area("Canais adicionais (um por linha)")
             days = st.number_input("Dias para filtrar", min_value=0, max_value=30, value=3)
-            max_videos = st.number_input("Limite de vídeos por canal", min_value=0, max_value=200, value=30)
+            max_videos = st.number_input(
+                "Limite de vídeos por canal", min_value=0, max_value=200, value=30
+            )
         with col2:
             prefix = st.text_input("Prefixo dos arquivos", value="youtube_extraction")
-            report_format = st.selectbox("Formato do relatório", options=["txt", "json", "pdf", "html"], index=0)
+            report_format = st.selectbox(
+                "Formato do relatório", options=["txt", "json", "pdf", "html"], index=0
+            )
             asr_provider = st.selectbox("Fornecedor de ASR", options=["faster-whisper", "openai"])
             no_asr = st.checkbox("Desativar ASR", value=False)
             llm_label = st.selectbox(
                 "Modelo LLM",
                 options=list(llm_options.keys()),
                 disabled=not llm_options,
             )
             resumo_max = st.number_input(
-                "Máximo de palavras no resumo", min_value=50, max_value=1000, value=settings.max_palavras_resumo
+                "Máximo de palavras no resumo",
+                min_value=50,
+                max_value=1000,
+                value=settings.max_palavras_resumo,
+                disabled=True,
+                help="Altere este valor pelo menu de Configurações.",
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
+    selected_labels = list(st.session_state.youtube_selected_channels)
     progress_container = st.container()
     results_container = st.container()
     if run_simple or run_full:
         mode = "simple" if run_simple else "full"
-        channels: list[str] = [options[label] for label in selected]
+        channels: list[str] = [
+            channel_options[label]
+            for label in selected_labels
+            if label in channel_options
+        ]
         if manual_entries:
             channels.extend([line.strip() for line in manual_entries.splitlines() if line.strip()])
-        if not selected:
+        if not selected_labels:
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
diff --git a/src/app/interfaces/web/pages/4_Execução.py b/src/app/interfaces/web/pages/4_Execução.py
index 48b93bee61bb63631d81ad36483beaf20eeef9b3..5d378340a6f824b7957cbde639f7871ce7672bba 100644
--- a/src/app/interfaces/web/pages/4_Execução.py
+++ b/src/app/interfaces/web/pages/4_Execução.py
@@ -138,37 +224,61 @@ else:
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
+                if result.channels_data:
+                    st.subheader("Origem da análise por vídeo")
+                    for channel_info in result.channels_data:
+                        channel_name = channel_info.get("name") or channel_info.get(
+                            "channel_id"
+                        )
+                        videos = channel_info.get("videos", [])
+                        expander_label = f"{channel_name} — {len(videos)} vídeo(s)"
+                        with st.expander(expander_label):
+                            if not videos:
+                                st.write("Nenhum vídeo analisado para este canal.")
+                            else:
+                                for video in videos:
+                                    video_title = video.get("title") or "Vídeo sem título"
+                                    video_url = video.get("url")
+                                    method_label = _analysis_method_label(
+                                        video.get("analysis_source")
+                                    )
+                                    if video_url:
+                                        st.markdown(
+                                            f"- [{video_title}]({video_url}) — {method_label}"
+                                        )
+                                    else:
+                                        st.markdown(f"- {video_title} — {method_label}")
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
 
EOF
)