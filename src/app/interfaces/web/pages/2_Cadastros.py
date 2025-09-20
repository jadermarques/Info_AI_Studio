from __future__ import annotations
import json
import streamlit as st
from app.domain.youtube.groups import split_channel_groups
from app.domain.entities import LLMModel, WebSource, YouTubeChannel
from app.domain.fonte_service import (
    list_web_sources,
    list_youtube_channels,
    register_web_source,
    register_youtube_channel,
    delete_youtube_channel,
    delete_web_source,
)
from app.domain.llm_service import (
    list_llm_models,
    register_llm_model,
    delete_llm_model,
)

# Helpers e estado
def _ensure_llm_state() -> None:
    defaults = {
        "llm_form_provedor": "",
        "llm_form_modelo": "",
        "llm_form_api_key": "",
        "llm_form_status": True,
        "llm_form_model_id": None,
    "llm_form_prefill": None,
    "llm_form_reset_pending": False,
        "llm_edit_confirm": None,
        "llm_delete_confirm": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_llm_form() -> None:
    st.session_state.llm_form_model_id = None
    st.session_state.llm_form_provedor = ""
    st.session_state.llm_form_modelo = ""
    st.session_state.llm_form_api_key = ""
    st.session_state.llm_form_status = True


def _populate_llm_form(row: dict) -> None:
    st.session_state.llm_form_model_id = row.get("id")
    st.session_state.llm_form_provedor = row.get("provedor", "")
    st.session_state.llm_form_modelo = row.get("modelo", "")
    st.session_state.llm_form_api_key = row.get("api_key", "")
    st.session_state.llm_form_status = bool(row.get("status", 1))


def _ensure_youtube_form_state() -> None:
    defaults = {
        "youtube_form_nome": "",
        "youtube_form_descricao": "",
        "youtube_form_grupos": [],
        "youtube_form_canal_id": "",
        "youtube_form_status": True,
        "youtube_form_registro_id": None,
        "youtube_form_reset_pending": False,
    "youtube_form_prefill": None,
        "youtube_edit_confirm": None,
        "youtube_delete_confirm": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _status_badge(is_active: bool) -> str:
    cor = "#27ae60" if is_active else "#c0392b"
    texto = "Ativo" if is_active else "Inativo"
    return f"<span style=\"color: white; background: {cor}; padding: 2px 8px; border-radius: 8px; font-size: 0.9em;\">{texto}</span>"

def format_channel_groups(grupos) -> str:
    """Formata grupos vindos como lista ou string (inclusive JSON)."""
    if isinstance(grupos, list):
        return ", ".join(map(str, grupos))
    if isinstance(grupos, str):
        s = grupos.strip()
        if not s:
            return "—"
        # tenta JSON de lista
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return ", ".join(map(str, parsed)) or "—"
        except Exception:
            pass
        return s
    return "—"

def _populate_youtube_form(row):
    st.session_state["youtube_form_nome"] = row.get("foyt_nome_canal", "")
    st.session_state["youtube_form_descricao"] = row.get("foyt_descricao", "")
    grupos_raw = row.get("foyt_grupo_canal", "")
    st.session_state["youtube_form_grupos"] = split_channel_groups(grupos_raw)
    st.session_state["youtube_form_canal_id"] = row.get("foyt_id_canal", "")
    st.session_state["youtube_form_status"] = row.get("foyt_status", False)
    st.session_state["youtube_form_registro_id"] = row.get("foyt_id", None)

# Reset do formulário (YouTube) só se a flag estiver setada antes dos widgets
if st.session_state.get("youtube_form_reset_pending"):
    st.session_state["youtube_form_nome"] = ""
    st.session_state["youtube_form_descricao"] = ""
    st.session_state["youtube_form_grupos"] = []
    st.session_state["youtube_form_canal_id"] = ""
    st.session_state["youtube_form_status"] = False
    st.session_state["youtube_form_registro_id"] = None
    st.session_state["youtube_form_reset_pending"] = False

# Reset do formulário (LLM) antes dos widgets
if st.session_state.get("llm_form_reset_pending"):
    _reset_llm_form()
    st.session_state["llm_form_reset_pending"] = False

# Aplicar prefill ANTES de instanciar os widgets
prefill_llm = st.session_state.get("llm_form_prefill")
if prefill_llm:
    # Espera o formato já normalizado vindo de list_llm_models
    st.session_state.llm_form_model_id = prefill_llm.get("id")
    st.session_state.llm_form_provedor = prefill_llm.get("provedor", "")
    st.session_state.llm_form_modelo = prefill_llm.get("modelo", "")
    st.session_state.llm_form_api_key = prefill_llm.get("api_key", "")
    st.session_state.llm_form_status = bool(prefill_llm.get("status", 1))
    st.session_state.llm_form_prefill = None

prefill_yt = st.session_state.get("youtube_form_prefill")
if prefill_yt:
    # Mapeia campos da tabela para widgets
    st.session_state["youtube_form_nome"] = prefill_yt.get("foyt_nome_canal", "")
    st.session_state["youtube_form_descricao"] = prefill_yt.get("foyt_descricao", "")
    grupos_raw = prefill_yt.get("foyt_grupo_canal", "")
    st.session_state["youtube_form_grupos"] = split_channel_groups(grupos_raw)
    st.session_state["youtube_form_canal_id"] = prefill_yt.get("foyt_id_canal", "")
    st.session_state["youtube_form_status"] = bool(prefill_yt.get("foyt_status", False))
    st.session_state["youtube_form_registro_id"] = prefill_yt.get("foyt_id", None)
    st.session_state["youtube_form_prefill"] = None

prefill_web = st.session_state.get("web_form_prefill")
if prefill_web:
    st.session_state["web_form_tipo"] = prefill_web.get("fowe_tipo", "site")
    st.session_state["web_form_fonte"] = prefill_web.get("fowe_fonte", "")
    st.session_state["web_form_descricao"] = prefill_web.get("fowe_descricao", "")
    st.session_state["web_form_status"] = bool(prefill_web.get("fowe_status", 0))
    st.session_state["web_form_registro_id"] = prefill_web.get("fowe_id")
    st.session_state["web_form_prefill"] = None

# Título e abas (fora do reset)
st.title("Cadastros")
_ensure_llm_state()
_ensure_youtube_form_state()
tab_llm, tab_youtube, tab_web = st.tabs(["Cadastro de LLM", "Cadastro Canais YouTube", "Cadastro Fontes Web"])

# --- ABA LLM ---
with tab_llm:
        st.header("Cadastro de Modelos LLM")
        # Formulário
        with st.form("llm_form"):
            provedor = st.text_input("Provedor", key="llm_form_provedor", placeholder="OPENAI")
            modelo = st.text_input("Modelo", key="llm_form_modelo", placeholder="gpt-5-nano")
            api_key = st.text_input("API Key", key="llm_form_api_key", type="password")
            ativo = st.checkbox("Ativo", key="llm_form_status")
            label_llm = "Atualizar modelo" if st.session_state.get("llm_form_model_id") is not None else "Salvar modelo"
            salvar = st.form_submit_button(label_llm, type="primary")
            if salvar:
                if not provedor or not modelo or not api_key:
                    st.error("Informe provedor, modelo e API key para salvar.")
                else:
                    try:
                        register_llm_model(
                            LLMModel(
                                provedor=provedor,
                                modelo=modelo,
                                api_key=api_key,
                                status=ativo,
                                model_id=st.session_state.llm_form_model_id,
                            )
                        )
                    except Exception as exc:
                        st.error(f"Erro ao salvar modelo: {exc}")
                    else:
                        st.success(f"Modelo {provedor}/{modelo} salvo com sucesso.")
                        st.session_state["llm_form_reset_pending"] = True
                        st.rerun()
        # Cancelar edição (LLM)
        if st.session_state.get("llm_form_model_id") is not None:
            if st.button("Cancelar edição", key="llm_cancel_edit"):
                st.session_state["llm_form_reset_pending"] = True
                st.rerun()
        # Tabela paginada
        llm_models = list_llm_models()
        page_llm = st.session_state.get("page_llm", 0)
        total_llm = len(llm_models)
        page_size = 10
        start_llm = page_llm * page_size
        end_llm = start_llm + page_size
        paginated_llm = llm_models[start_llm:end_llm]
        st.write(f"Exibindo {start_llm+1} a {min(end_llm, total_llm)} de {total_llm}")
        col_pag_llm1, col_pag_llm2 = st.columns([1,1])
        if col_pag_llm1.button("Página anterior", disabled=page_llm==0, key="llm_prev"):
            st.session_state.page_llm = max(page_llm-1, 0)
            st.rerun()
        if col_pag_llm2.button("Próxima página", disabled=end_llm>=total_llm, key="llm_next"):
            st.session_state.page_llm = page_llm+1
            st.rerun()
        # Tabela
        if paginated_llm:
            header = st.columns([2,2,3,1,2,1,1])
            header[0].markdown("**Provedor**")
            header[1].markdown("**Modelo**")
            header[2].markdown("**API Key**")
            header[3].markdown("**Status**")
            header[4].markdown("**Data de criação**")
            header[5].markdown("**Editar**")
            header[6].markdown("**Excluir**")
            for row in paginated_llm:
                cols = st.columns([2,2,3,1,2,1,1])
                cols[0].markdown(row["provedor"])
                cols[1].markdown(row["modelo"])
                cols[2].markdown(f"`{row['api_key']}`")
                cols[3].markdown(_status_badge(row["status"]), unsafe_allow_html=True)
                cols[4].markdown(row["created_at"])
                if cols[5].button("✏️", key=f"llm_edit_{row['id']}", help="Editar modelo"):
                    st.session_state.llm_edit_confirm = row['id']
                if cols[6].button("🗑️", key=f"llm_delete_{row['id']}", help="Excluir modelo"):
                    st.session_state.llm_delete_confirm = row['id']
        # Confirmação de edição
        if st.session_state.get("llm_edit_confirm") is not None:
            edit_id = st.session_state.llm_edit_confirm
            edit_row = next((r for r in llm_models if r["id"] == edit_id), None)
            if edit_row:
                st.warning(f"Confirma editar o modelo {edit_row['provedor']} / {edit_row['modelo']}?")
                col1, col2 = st.columns(2)
                if col1.button("Confirmar edição", key="confirm_llm_edit"):
                    st.session_state.llm_form_prefill = edit_row
                    st.session_state.llm_edit_confirm = None
                    st.rerun()
                if col2.button("Cancelar", key="cancel_llm_edit_confirm"):
                    st.session_state.llm_edit_confirm = None
                    st.rerun()
        # Confirmação de exclusão
        if st.session_state.get("llm_delete_confirm") is not None:
            del_id = st.session_state.llm_delete_confirm
            del_row = next((r for r in llm_models if r["id"] == del_id), None)
            if del_row:
                st.warning(f"Confirma excluir o modelo {del_row['provedor']} / {del_row['modelo']}?")
                col1, col2 = st.columns(2)
                if col1.button("Confirmar exclusão", key="confirm_llm_delete"):
                    delete_llm_model(del_id)
                    st.success(f"Modelo {del_row['provedor']} / {del_row['modelo']} removido.")
                    st.session_state.llm_delete_confirm = None
                    st.rerun()
                if col2.button("Cancelar", key="cancel_llm_delete_confirm"):
                    st.session_state.llm_delete_confirm = None
                    st.rerun()

# --- ABA YOUTUBE ---
with tab_youtube:
        st.header("Cadastro de Canais YouTube")
        from app.domain.youtube.groups import YOUTUBE_CHANNEL_GROUP_OPTIONS
        with st.form("youtube_form"):
            nome = st.text_input("Nome do canal", key="youtube_form_nome")
            descricao = st.text_area("Descrição", key="youtube_form_descricao")
            grupos = st.multiselect("Grupo(s) do canal", options=YOUTUBE_CHANNEL_GROUP_OPTIONS, key="youtube_form_grupos")
            canal_id = st.text_input("ID do canal", key="youtube_form_canal_id", placeholder="@exemplo")
            ativo_canal = st.checkbox("Ativo", key="youtube_form_status")
            label_youtube = "Atualizar canal" if st.session_state.get("youtube_form_registro_id") else "Salvar canal"
            salvar_canal = st.form_submit_button(label_youtube, type="primary")
            if salvar_canal:
                if not nome:
                    st.error("Informe o nome do canal.")
                elif not grupos:
                    st.error("Selecione ao menos um grupo para o canal.")
                elif not canal_id:
                    st.error("Informe o ID do canal.")
                else:
                    try:
                        register_youtube_channel(
                            YouTubeChannel(
                                nome=nome,
                                descricao=descricao,
                                grupos=grupos,
                                canal_id=canal_id,
                                status=ativo_canal,
                                registro_id=st.session_state.get("youtube_form_registro_id")
                            )
                        )
                    except Exception as exc:
                        st.error(f"Erro ao salvar canal: {exc}")
                    else:
                        st.success(f"Canal {nome} salvo com sucesso.")
                        st.session_state.youtube_form_registro_id = None
                        st.rerun()
        # Cancelar edição (YouTube)
        if st.session_state.get("youtube_form_registro_id"):
            if st.button("Cancelar edição", key="youtube_cancel_edit"):
                st.session_state["youtube_form_reset_pending"] = True
                st.session_state["youtube_form_registro_id"] = None
                st.rerun()
        # Tabela paginada
        youtube_channels = list_youtube_channels(active_only=False)
        page_youtube = st.session_state.get("page_youtube", 0)
        total_youtube = len(youtube_channels)
        page_size = 10
        start_youtube = page_youtube * page_size
        end_youtube = start_youtube + page_size
        paginated_youtube = youtube_channels[start_youtube:end_youtube]
        st.write(f"Exibindo {start_youtube+1} a {min(end_youtube, total_youtube)} de {total_youtube}")
        col_pag_y1, col_pag_y2 = st.columns([1,1])
        if col_pag_y1.button("Página anterior", disabled=page_youtube==0, key="youtube_prev"):
            st.session_state.page_youtube = max(page_youtube-1, 0)
            st.rerun()
        if col_pag_y2.button("Próxima página", disabled=end_youtube>=total_youtube, key="youtube_next"):
            st.session_state.page_youtube = page_youtube+1
            st.rerun()
        # Tabela
        if paginated_youtube:
            header = st.columns([2,3,3,2,1,2,1,1])
            header[0].markdown("**Nome do canal**")
            header[1].markdown("**Descrição**")
            header[2].markdown("**Grupo(s) do canal**")
            header[3].markdown("**ID do canal**")
            header[4].markdown("**Status**")
            header[5].markdown("**Data criação**")
            header[6].markdown("**Editar**")
            header[7].markdown("**Excluir**")
            for row in paginated_youtube:
                grupos_texto = format_channel_groups(row.get("foyt_grupo_canal", ""))
                ativo = bool(row.get("foyt_status", 0))
                cols = st.columns([2,3,3,2,1,2,1,1])
                cols[0].markdown(row.get("foyt_nome_canal", "—"))
                cols[1].markdown(row.get("foyt_descricao") or "—")
                cols[2].markdown(grupos_texto or "—")
                cols[3].markdown(row.get("foyt_id_canal", "—"))
                cols[4].markdown(_status_badge(ativo), unsafe_allow_html=True)
                cols[5].markdown(row.get("foyt_created_at", "—"))
                if cols[6].button("✏️", key=f"youtube_edit_{row['foyt_id']}", help="Editar canal"):
                    st.session_state.youtube_edit_confirm = row['foyt_id']
                if cols[7].button("🗑️", key=f"youtube_delete_{row['foyt_id']}", help="Excluir canal"):
                    st.session_state.youtube_delete_confirm = row['foyt_id']
        # Confirmação de edição
        if st.session_state.get("youtube_edit_confirm") is not None:
            edit_id = st.session_state.youtube_edit_confirm
            edit_row = next((r for r in youtube_channels if r["foyt_id"] == edit_id), None)
            if edit_row:
                st.warning(f"Confirma editar o canal {edit_row.get('foyt_nome_canal','')}?")
                col1, col2 = st.columns(2)
                if col1.button("Confirmar edição", key="confirm_youtube_edit"):
                    st.session_state["youtube_form_prefill"] = edit_row
                    st.session_state.youtube_edit_confirm = None
                    st.rerun()
                if col2.button("Cancelar", key="cancel_youtube_edit_confirm"):
                    st.session_state.youtube_edit_confirm = None
                    st.rerun()
        # Confirmação de exclusão
        if st.session_state.get("youtube_delete_confirm") is not None:
            del_id = st.session_state.youtube_delete_confirm
            del_row = next((r for r in youtube_channels if r["foyt_id"] == del_id), None)
            if del_row:
                st.warning(f"Confirma excluir o canal {del_row.get('foyt_nome_canal','')}?")
                col1, col2 = st.columns(2)
                if col1.button("Confirmar exclusão", key="confirm_youtube_delete"):
                    delete_youtube_channel(del_id)
                    st.success(f"Canal {del_row.get('foyt_nome_canal','')} removido.")
                    st.session_state.youtube_delete_confirm = None
                    st.rerun()
                if col2.button("Cancelar", key="cancel_youtube_delete_confirm"):
                    st.session_state.youtube_delete_confirm = None
                    st.rerun()

# --- ABA FONTES WEB ---
with tab_web:
        st.header("Cadastro de Fontes Web")
        with st.form("web_form"):
            tipo = st.selectbox("Tipo", options=["site", "blog", "youtube"], key="web_form_tipo")
            fonte = st.text_input("Fonte", placeholder="https://exemplo.com", key="web_form_fonte")
            descricao_fonte = st.text_area("Descrição", key="web_form_descricao")
            status = st.checkbox("Ativo", value=True, key="web_form_status")
            label_web = "Atualizar fonte" if st.session_state.get("web_form_registro_id") else "Salvar fonte"
            salvar_fonte = st.form_submit_button(label_web, type="primary")
            if salvar_fonte:
                if not fonte or not descricao_fonte:
                    st.error("Fonte e descrição são obrigatórias.")
                else:
                    try:
                        register_web_source(
                            WebSource(tipo=tipo, fonte=fonte, descricao=descricao_fonte, status=status),
                            entry_id=st.session_state.get("web_form_registro_id")
                        )
                    except Exception as exc:
                        st.error(f"Erro ao salvar fonte: {exc}")
                    else:
                        st.success(f"Fonte {fonte} salva com sucesso.")
                        st.session_state["web_form_registro_id"] = None
                        st.rerun()
        # Cancelar edição (Web)
        if st.session_state.get("web_form_registro_id"):
            if st.button("Cancelar edição", key="web_cancel_edit"):
                st.session_state["web_form_registro_id"] = None
                st.session_state["web_form_tipo"] = "site"
                st.session_state["web_form_fonte"] = ""
                st.session_state["web_form_descricao"] = ""
                st.session_state["web_form_status"] = True
                st.rerun()
        # Tabela paginada
        web_sources = list_web_sources(active_only=False)
        page_web = st.session_state.get("page_web", 0)
        total_web = len(web_sources)
        page_size = 10
        start_web = page_web * page_size
        end_web = start_web + page_size
        paginated_web = web_sources[start_web:end_web]
        st.write(f"Exibindo {start_web+1} a {min(end_web, total_web)} de {total_web}")
        col_pag_w1, col_pag_w2 = st.columns([1,1])
        if col_pag_w1.button("Página anterior", disabled=page_web==0, key="web_prev"):
            st.session_state.page_web = max(page_web-1, 0)
            st.rerun()
        if col_pag_w2.button("Próxima página", disabled=end_web>=total_web, key="web_next"):
            st.session_state.page_web = page_web+1
            st.rerun()
        # Tabela
        if paginated_web:
            header = st.columns([2,3,3,1,1,1])
            header[0].markdown("**Tipo**")
            header[1].markdown("**Fonte**")
            header[2].markdown("**Descrição**")
            header[3].markdown("**Status**")
            header[4].markdown("**Editar**")
            header[5].markdown("**Excluir**")
            for row in paginated_web:
                cols = st.columns([2,3,3,1,1,1])
                cols[0].markdown(row.get('fowe_tipo',''))
                cols[1].markdown(row.get('fowe_fonte',''))
                cols[2].markdown(row.get('fowe_descricao',''))
                cols[3].markdown(_status_badge(bool(row.get('fowe_status',0))), unsafe_allow_html=True)
                if cols[4].button("✏️", key=f"web_edit_{row.get('fowe_id', row.get('fowe_fonte', ''))}", help="Editar fonte"):
                    st.session_state.web_edit_confirm = row.get('fowe_id', None)
                if cols[5].button("🗑️", key=f"web_delete_{row.get('fowe_id', row.get('fowe_fonte', ''))}", help="Excluir fonte"):
                    st.session_state.web_delete_confirm = row.get('fowe_id', None)
        # Confirmação de edição
        if st.session_state.get("web_edit_confirm") is not None:
            edit_id = st.session_state.web_edit_confirm
            edit_row = next((r for r in web_sources if r.get('fowe_id', None) == edit_id), None)
            if edit_row:
                st.warning(f"Confirma editar a fonte {edit_row.get('fowe_fonte','')}?")
                col1, col2 = st.columns(2)
                if col1.button("Confirmar edição", key="confirm_web_edit"):
                    st.session_state["web_form_prefill"] = edit_row
                    st.session_state.web_edit_confirm = None
                    st.rerun()
                if col2.button("Cancelar", key="cancel_web_edit_confirm"):
                    st.session_state.web_edit_confirm = None
                    st.rerun()
        # Confirmação de exclusão
        if st.session_state.get("web_delete_confirm") is not None:
            del_id = st.session_state.web_delete_confirm
            del_row = next((r for r in web_sources if r.get('fowe_id', None) == del_id), None)
            if del_row:
                st.warning(f"Confirma excluir a fonte {del_row.get('fowe_fonte','')}?")
                col1, col2 = st.columns(2)
                if col1.button("Confirmar exclusão", key="confirm_web_delete"):
                    delete_web_source(del_id)
                    st.success(f"Fonte {del_row.get('fowe_fonte','')} removida.")
                    st.session_state.web_delete_confirm = None
                    st.rerun()
                if col2.button("Cancelar", key="cancel_web_delete_confirm"):
                    st.session_state.web_delete_confirm = None
                    st.rerun()
    

# --- ABA FONTES WEB ---
# Bloco duplicado removido para evitar conflito de keys em formulários.
