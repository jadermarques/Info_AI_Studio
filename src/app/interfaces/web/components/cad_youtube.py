from __future__ import annotations

import json
import streamlit as st
from typing import Any
from app.domain.entities import YouTubeChannel
from app.domain.fonte_service import list_youtube_channels, register_youtube_channel, delete_youtube_channel
from app.domain.youtube.groups import split_channel_groups
from .ui_helpers import status_badge, paginate, render_pagination_controls


STATE_DEFAULTS = {
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


def ensure_state() -> None:
    for k, v in STATE_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def format_channel_groups(grupos: Any) -> str:
    if isinstance(grupos, list):
        return ", ".join(map(str, grupos))
    if isinstance(grupos, str):
        s = grupos.strip()
        if not s:
            return "—"
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return ", ".join(map(str, parsed)) or "—"
        except Exception:
            pass
        return s
    return "—"


def apply_prefill_and_resets() -> None:
    if st.session_state.get("youtube_form_reset_pending"):
        st.session_state["youtube_form_nome"] = ""
        st.session_state["youtube_form_descricao"] = ""
        st.session_state["youtube_form_grupos"] = []
        st.session_state["youtube_form_canal_id"] = ""
        st.session_state["youtube_form_status"] = False
        st.session_state["youtube_form_registro_id"] = None
        st.session_state["youtube_form_reset_pending"] = False
    prefill = st.session_state.get("youtube_form_prefill")
    if prefill:
        st.session_state["youtube_form_nome"] = prefill.get("foyt_nome_canal", "")
        st.session_state["youtube_form_descricao"] = prefill.get("foyt_descricao", "")
        st.session_state["youtube_form_grupos"] = split_channel_groups(prefill.get("foyt_grupo_canal", ""))
        st.session_state["youtube_form_canal_id"] = prefill.get("foyt_id_canal", "")
        st.session_state["youtube_form_status"] = bool(prefill.get("foyt_status", False))
        st.session_state["youtube_form_registro_id"] = prefill.get("foyt_id", None)
        st.session_state["youtube_form_prefill"] = None


def render() -> None:
    ensure_state()
    apply_prefill_and_resets()

    st.header("Cadastro de Canais YouTube")
    from app.domain.youtube.groups import YOUTUBE_CHANNEL_GROUP_OPTIONS
    with st.form("youtube_form"):
        nome = st.text_input("Nome do canal", key="youtube_form_nome")
        descricao = st.text_area("Descrição", key="youtube_form_descricao")
        grupos = st.multiselect("Grupo(s) do canal", options=YOUTUBE_CHANNEL_GROUP_OPTIONS, key="youtube_form_grupos")
        canal_id = st.text_input("ID do canal", key="youtube_form_canal_id", placeholder="@exemplo")
        ativo_canal = st.checkbox("Ativo", key="youtube_form_status")
        label = "Atualizar canal" if st.session_state.get("youtube_form_registro_id") else "Salvar canal"
        salvar = st.form_submit_button(label, type="primary")
        if salvar:
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
                            registro_id=st.session_state.get("youtube_form_registro_id"),
                        )
                    )
                except Exception as exc:
                    st.error(f"Erro ao salvar canal: {exc}")
                else:
                    st.success(f"Canal {nome} salvo com sucesso.")
                    st.session_state["youtube_form_registro_id"] = None
                    st.session_state["youtube_form_reset_pending"] = True
                    st.rerun()

    if st.session_state.get("youtube_form_registro_id"):
        if st.button("Cancelar edição", key="youtube_cancel_edit"):
            st.session_state["youtube_form_reset_pending"] = True
            st.session_state["youtube_form_registro_id"] = None
            st.rerun()

    registros = list_youtube_channels(active_only=False)
    paginated, page, start, end = paginate(registros, "page_youtube")
    st.write(f"Exibindo {start+1} a {end} de {len(registros)}")
    render_pagination_controls("page_youtube", page, end, len(registros), "youtube_prev", "youtube_next", size_key="page_youtube_size")

    if paginated:
        header = st.columns([2,3,3,2,1,2,1,1])
        header[0].markdown("**Nome do canal**")
        header[1].markdown("**Descrição**")
        header[2].markdown("**Grupo(s) do canal**")
        header[3].markdown("**ID do canal**")
        header[4].markdown("**Status**")
        header[5].markdown("**Data criação**")
        header[6].markdown("**Editar**")
        header[7].markdown("**Excluir**")
        for row in paginated:
            grupos_texto = format_channel_groups(row.get("foyt_grupo_canal", ""))
            ativo = bool(row.get("foyt_status", 0))
            cols = st.columns([2,3,3,2,1,2,1,1])
            cols[0].markdown(row.get("foyt_nome_canal", "—"))
            cols[1].markdown(row.get("foyt_descricao") or "—")
            cols[2].markdown(grupos_texto or "—")
            cols[3].markdown(row.get("foyt_id_canal", "—"))
            cols[4].markdown(status_badge(ativo), unsafe_allow_html=True)
            cols[5].markdown(row.get("foyt_created_at", "—"))
            if cols[6].button("✏️", key=f"youtube_edit_{row['foyt_id']}", help="Editar canal"):
                st.session_state.youtube_edit_confirm = row['foyt_id']
            if cols[7].button("🗑️", key=f"youtube_delete_{row['foyt_id']}", help="Excluir canal"):
                st.session_state.youtube_delete_confirm = row['foyt_id']

    if st.session_state.get("youtube_edit_confirm") is not None:
        edit_id = st.session_state.youtube_edit_confirm
        edit_row = next((r for r in registros if r["foyt_id"] == edit_id), None)
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

    if st.session_state.get("youtube_delete_confirm") is not None:
        del_id = st.session_state.youtube_delete_confirm
        del_row = next((r for r in registros if r["foyt_id"] == del_id), None)
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
