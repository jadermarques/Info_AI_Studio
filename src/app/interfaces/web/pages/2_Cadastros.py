from __future__ import annotations
import streamlit as st
from app.domain.youtube.groups import split_channel_groups

def _populate_youtube_form(row):
    st.session_state["youtube_form_nome"] = row.get("foyt_nome_canal", "")
    st.session_state["youtube_form_descricao"] = row.get("foyt_descricao", "")
    grupos_raw = row.get("foyt_grupo_canal", "")
    st.session_state["youtube_form_grupos"] = split_channel_groups(grupos_raw)
    st.session_state["youtube_form_canal_id"] = row.get("foyt_id_canal", "")
    st.session_state["youtube_form_status"] = row.get("foyt_status", False)
    st.session_state["youtube_form_registro_id"] = row.get("foyt_id", None)
import streamlit as st

# Reset do formulário só se a flag estiver setada antes dos widgets

# Reset do formulário só se a flag estiver setada antes dos widgets
if st.session_state.get("youtube_form_reset_pending"):
    st.session_state["youtube_form_nome"] = ""
    st.session_state["youtube_form_descricao"] = ""
    st.session_state["youtube_form_grupos"] = []
    st.session_state["youtube_form_canal_id"] = ""
    st.session_state["youtube_form_status"] = False
    st.session_state["youtube_form_registro_id"] = None
    st.session_state["youtube_form_reset_pending"] = False

def _reset_youtube_form():
    pass  # Reset é feito no início do script, nunca após widgets

def format_channel_groups(grupos):
    if isinstance(grupos, list):
        return ", ".join(grupos)
    if isinstance(grupos, str):
        return grupos
    return ""
"""Página de cadastros (LLM, canais e fontes)."""

from typing import Any

import streamlit as st

from app.domain.entities import LLMModel, WebSource, YouTubeChannel
from app.domain.fonte_service import (
    list_web_sources,
    list_youtube_channels,
    register_web_source,
    register_youtube_channel,
    delete_youtube_channel,
)
from app.domain.llm_service import (
    LLMConnectionError,
    compute_api_key_env_name,
    delete_llm_model,
    list_llm_models,
    register_llm_model,
    test_llm_connection,
)


def _ensure_llm_state() -> None:
    defaults = {
        "llm_form_provedor": "",
        "llm_form_modelo": "",
        "llm_form_api_key": "",
        "llm_form_status": True,
        "llm_form_model_id": None,
        "llm_test_feedback": None,
        "llm_flash": None,
        "llm_delete_pending": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _ensure_youtube_form_state() -> None:
    defaults = {
        "youtube_form_nome": "",
        "youtube_form_descricao": "",
        "youtube_form_grupo": "",
        "youtube_form_canal_id": "",
        "youtube_form_status": True,
        "youtube_form_reset_pending": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_llm_form() -> None:
    st.session_state.llm_form_model_id = None
    st.session_state.llm_form_provedor = ""
    st.session_state.llm_form_modelo = ""
    st.session_state.llm_form_api_key = ""
    st.session_state.llm_form_status = True


def _populate_llm_form(row: dict[str, Any]) -> None:
    st.session_state.llm_form_model_id = row["id"]
    st.session_state.llm_form_provedor = row["provedor"]
    st.session_state.llm_form_modelo = row["modelo"]
    st.session_state.llm_form_api_key = row["api_key"]
    st.session_state.llm_form_status = row["status"]


def _status_badge(is_active: bool) -> str:
    cor = "green" if is_active else "red"
    texto = "Ativo" if is_active else "Inativo"
    return f"<span style='color:{cor}; font-weight:bold;'>●</span> {texto}"


def _record_test_feedback(success: bool, message: str, env_var: str) -> None:
    st.session_state.llm_test_feedback = {
        "type": "success" if success else "error",
        "message": message,
        "env_var": env_var,
    }

st.title("Cadastros")

_ensure_llm_state()
_ensure_youtube_form_state()

st.subheader("Modelos LLM")

flash_message = st.session_state.llm_flash
if flash_message:
    level, message = flash_message
    if level == "success":
        st.success(message)
    else:
        st.error(message)
    st.session_state.llm_flash = None

pending_delete = st.session_state.llm_delete_pending
if pending_delete is not None:
    with st.container():
        st.warning(
            "Confirma excluir o modelo "
            f"{pending_delete['provedor']} / {pending_delete['modelo']}?"
        )
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button("Excluir", type="primary", key="confirm_delete_llm"):
            delete_llm_model(pending_delete["id"])
            st.session_state.llm_flash = (
                "success",
                f"Modelo {pending_delete['provedor']} / {pending_delete['modelo']} removido.",
            )
            if st.session_state.llm_form_model_id == pending_delete["id"]:
                _reset_llm_form()
            st.session_state.llm_delete_pending = None
            st.rerun()
        if cancel_col.button("Cancelar", key="cancel_delete_llm"):
            st.session_state.llm_delete_pending = None
            st.rerun()

with st.form("llm_form"):
    col1, col2 = st.columns(2)
    with col1:
        provedor = st.text_input("Provedor", key="llm_form_provedor", placeholder="OPENAI")
        modelo = st.text_input("Modelo", key="llm_form_modelo", placeholder="gpt-5-nano")
    with col2:
        api_key = st.text_input("API Key", key="llm_form_api_key", type="password")
        ativo = st.checkbox("Ativo", key="llm_form_status")
    if provedor:
        st.caption(
            f"Variável de ambiente: {compute_api_key_env_name(provedor)}"
        )
    col_save, col_test = st.columns(2)
    with col_save:
        salvar = st.form_submit_button("Salvar modelo", type="primary")
    with col_test:
        testar = st.form_submit_button("Testar conexão", type="secondary")

    model_id = st.session_state.llm_form_model_id
    if salvar:
        if not provedor or not modelo or not api_key:
            st.session_state.llm_flash = (
                "error",
                "Informe provedor, modelo e API key para salvar.",
            )
        else:
            try:
                register_llm_model(
                    LLMModel(
                        provedor=provedor,
                        modelo=modelo,
                        api_key=api_key,
                        status=ativo,
                        model_id=model_id,
                    )
                )
            except Exception as exc:  # pragma: no cover - depende do provedor
                st.session_state.llm_flash = ("error", str(exc))
            else:
                st.session_state.llm_flash = (
                    "success",
                    f"Modelo {provedor}/{modelo} salvo com sucesso.",
                )
                _reset_llm_form()
        st.rerun()
    if testar:
        if not provedor or not modelo or not api_key:
            _record_test_feedback(
                False,
                "Informe provedor, modelo e API key para testar a conexão.",
                compute_api_key_env_name(provedor),
            )
        else:
            try:
                resultado = test_llm_connection(
                    LLMModel(
                        provedor=provedor,
                        modelo=modelo,
                        api_key=api_key,
                        status=ativo,
                        model_id=model_id,
                    )
                )
            except LLMConnectionError as err:
                _record_test_feedback(False, err.message, err.env_var)
            except Exception as exc:  # pragma: no cover - depende do provedor
                _record_test_feedback(
                    False,
                    str(exc),
                    compute_api_key_env_name(provedor),
                )
            else:
                _record_test_feedback(True, resultado.mensagem, resultado.variavel_ambiente)
        st.rerun()

if st.session_state.llm_form_model_id is not None:
    st.info(
        "Editando modelo ID "
        f"{st.session_state.llm_form_model_id}."
    )
    if st.button("Cancelar edição", key="cancel_llm_edit"):
        _reset_llm_form()
        st.rerun()

feedback = st.session_state.llm_test_feedback
if feedback:
    texto = feedback["message"]
    if feedback.get("env_var"):
        texto = f"{texto} (variável {feedback['env_var']})"
    if feedback["type"] == "success":
        st.success(texto)
    else:
        st.error(texto)

llm_models = list_llm_models()
if not llm_models:
    st.info("Nenhum modelo cadastrado ainda.")
else:
    header_cols = st.columns([2, 2, 3, 1, 2, 2])
    header_cols[0].markdown("**Provedor**")
    header_cols[1].markdown("**Modelo**")
    header_cols[2].markdown("**API Key**")
    header_cols[3].markdown("**Status**")
    header_cols[4].markdown("**Data de criação**")
    header_cols[5].markdown("**Ações**")
    for row in llm_models:
        row_cols = st.columns([2, 2, 3, 1, 2, 2])
        row_cols[0].markdown(row["provedor"])
        row_cols[1].markdown(row["modelo"])
        row_cols[2].markdown(f"`{row['api_key']}`")
        row_cols[3].markdown(_status_badge(row["status"]), unsafe_allow_html=True)
        row_cols[4].markdown(row["created_at"])
        action_cols = row_cols[5].columns(3)
        if action_cols[0].button("✏️", key=f"llm_edit_{row['id']}", help="Editar modelo"):
            _populate_llm_form(row)
            st.session_state.llm_delete_pending = None
            st.rerun()
        if action_cols[1].button("🧪", key=f"llm_test_{row['id']}", help="Testar modelo"):
            try:
                resultado = test_llm_connection(
                    LLMModel(
                        provedor=row["provedor"],
                        modelo=row["modelo"],
                        api_key=row["api_key"],
                        status=row["status"],
                        model_id=row["id"],
                    )
                )
            except LLMConnectionError as err:
                _record_test_feedback(False, err.message, err.env_var)
            except Exception as exc:  # pragma: no cover - depende do provedor
                _record_test_feedback(False, str(exc), row.get("env_var", ""))
            else:
                _record_test_feedback(True, resultado.mensagem, resultado.variavel_ambiente)
            st.rerun()
        if action_cols[2].button("🗑️", key=f"llm_delete_{row['id']}", help="Excluir modelo"):
            st.session_state.llm_delete_pending = row
            st.rerun()

st.divider()

st.subheader("Canais do YouTube")
if "youtube_form_flash" not in st.session_state:
    st.session_state["youtube_form_flash"] = None
youtube_flash = st.session_state.youtube_form_flash
if youtube_flash:
    level, message = youtube_flash
    if level == "success":
        st.success(message)
    else:
        st.error(message)
    st.session_state.youtube_form_flash = None

if "youtube_delete_pending" not in st.session_state:
    st.session_state["youtube_delete_pending"] = None
delete_candidate = st.session_state.youtube_delete_pending
if delete_candidate is not None:
    with st.container():
        st.warning(
            "Confirma excluir o canal "
            f"{delete_candidate['foyt_nome_canal']} ({delete_candidate['foyt_id_canal']})?"
        )
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button("Excluir", type="primary", key="confirm_delete_youtube"):
            delete_youtube_channel(delete_candidate["foyt_id"])
            st.session_state.youtube_form_flash = (
                "success",
                f"Canal {delete_candidate['foyt_nome_canal']} removido.",
            )
            if (
                st.session_state.youtube_form_registro_id
                == delete_candidate.get("foyt_id")
            ):
                _reset_youtube_form()
            st.session_state.youtube_delete_pending = None
            st.rerun()
        if cancel_col.button("Cancelar", key="cancel_delete_youtube"):
            st.session_state.youtube_delete_pending = None
            st.rerun()


from app.domain.youtube.groups import YOUTUBE_CHANNEL_GROUP_OPTIONS

with st.form("youtube_form"):
    st.text_input("Nome do canal", key="youtube_form_nome")
    st.text_area("Descrição", key="youtube_form_descricao")
    st.multiselect(
        "Grupo(s) do canal",
        options=YOUTUBE_CHANNEL_GROUP_OPTIONS,
        key="youtube_form_grupos",
        help="Selecione um ou mais grupos predefinidos.",
    )
    st.text_input("ID do canal", key="youtube_form_canal_id", placeholder="@exemplo")
    st.checkbox("Ativo", key="youtube_form_status")
    submit_channel = st.form_submit_button("Salvar canal", type="primary")
    if submit_channel:
        nome = st.session_state["youtube_form_nome"].strip()
        descricao = st.session_state["youtube_form_descricao"].strip()
        grupos = st.session_state["youtube_form_grupos"]
        canal_id = st.session_state["youtube_form_canal_id"].strip()
        ativo_canal = st.session_state["youtube_form_status"]
        registro_id = st.session_state.youtube_form_registro_id
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
                        registro_id=registro_id,
                    )
                )
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:  # pragma: no cover - depende da camada de dados
                st.error(f"Não foi possível salvar o canal: {exc}")
            else:
                mensagem = (
                    "Canal atualizado com sucesso."
                    if registro_id is not None
                    else "Canal salvo com sucesso."
                )
                st.session_state.youtube_form_flash = ("success", mensagem)
                st.session_state.youtube_form_reset_pending = True
                st.rerun()

if "youtube_form_registro_id" not in st.session_state:
    st.session_state["youtube_form_registro_id"] = None
if st.session_state.youtube_form_registro_id is not None:
    st.info(
        "Editando canal ID "
        f"{st.session_state.youtube_form_registro_id}."
    )
    if st.button("Cancelar edição", key="cancel_youtube_edit"):
        _reset_youtube_form()
        st.rerun()

youtube_channels = list_youtube_channels(active_only=False)
if not youtube_channels:
    st.info("Nenhum canal cadastrado ainda.")
else:
    header_cols = st.columns([2, 3, 3, 2, 1, 2, 0.8, 0.8])
    header_cols[0].markdown("**Nome do canal**")
    header_cols[1].markdown("**Descrição**")
    header_cols[2].markdown("**Grupo(s) do canal**")
    header_cols[3].markdown("**ID do canal**")
    header_cols[4].markdown("**Status**")
    header_cols[5].markdown("**Data criação**")
    header_cols[6].markdown("**Editar**")
    header_cols[7].markdown("**Excluir**")
    for row in youtube_channels:
        grupos_texto = format_channel_groups(row.get("foyt_grupo_canal", ""))
        ativo = bool(row.get("foyt_status", 0))
        row_cols = st.columns([2, 3, 3, 2, 1, 2, 0.8, 0.8])
        row_cols[0].markdown(row.get("foyt_nome_canal", "—"))
        row_cols[1].markdown(row.get("foyt_descricao") or "—")
        row_cols[2].markdown(grupos_texto or "—")
        row_cols[3].markdown(row.get("foyt_id_canal", "—"))
        row_cols[4].markdown(_status_badge(ativo), unsafe_allow_html=True)
        row_cols[5].markdown(row.get("foyt_created_at", "—"))
        if row_cols[6].button(
            "✏️",
            key=f"youtube_edit_{row['foyt_id']}",
            help="Editar canal",
        ):
            st.session_state.youtube_edit_pending = row
            st.session_state.youtube_form_flash = None
            st.session_state.youtube_delete_pending = None
            st.rerun()
        if row_cols[7].button(
            "🗑️",
            key=f"youtube_delete_{row['foyt_id']}",
            help="Excluir canal",
        ):
            st.session_state.youtube_delete_pending = row
            st.rerun()

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
