from __future__ import annotations

import streamlit as st
from app.domain.entities import WebSource
from app.domain.fonte_service import list_web_sources, register_web_source, delete_web_source
from .ui_helpers import status_badge, paginate, render_pagination_controls


STATE_DEFAULTS = {
    "web_form_tipo": "site",
    "web_form_fonte": "",
    "web_form_descricao": "",
    "web_form_status": True,
    "web_form_registro_id": None,
    "web_form_prefill": None,
    "web_form_reset_pending": False,
    "web_edit_confirm": None,
    "web_delete_confirm": None,
}


def ensure_state() -> None:
    for k, v in STATE_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def apply_prefill_and_resets() -> None:
    if st.session_state.get("web_form_reset_pending"):
        st.session_state["web_form_tipo"] = "site"
        st.session_state["web_form_fonte"] = ""
        st.session_state["web_form_descricao"] = ""
        st.session_state["web_form_status"] = True
        st.session_state["web_form_registro_id"] = None
        st.session_state["web_form_reset_pending"] = False
    prefill = st.session_state.get("web_form_prefill")
    if prefill:
        st.session_state["web_form_tipo"] = prefill.get("fowe_tipo", "site")
        st.session_state["web_form_fonte"] = prefill.get("fowe_fonte", "")
        st.session_state["web_form_descricao"] = prefill.get("fowe_descricao", "")
        st.session_state["web_form_status"] = bool(prefill.get("fowe_status", 0))
        st.session_state["web_form_registro_id"] = prefill.get("fowe_id")
        st.session_state["web_form_prefill"] = None


def render() -> None:
    ensure_state()
    apply_prefill_and_resets()

    st.header("Cadastro de Fontes Web")

    with st.form("web_form"):
        tipo = st.selectbox("Tipo", options=["site", "blog", "youtube"], key="web_form_tipo")
        fonte = st.text_input("Fonte", placeholder="https://exemplo.com", key="web_form_fonte")
        descricao_fonte = st.text_area("Descrição", key="web_form_descricao")
        status = st.checkbox("Ativo", key="web_form_status")
        label = "Atualizar fonte" if st.session_state.get("web_form_registro_id") else "Salvar fonte"
        salvar = st.form_submit_button(label, type="primary")
        if salvar:
            if not fonte or not descricao_fonte:
                st.error("Fonte e descrição são obrigatórias.")
            else:
                try:
                    register_web_source(
                        WebSource(tipo=tipo, fonte=fonte, descricao=descricao_fonte, status=status),
                        entry_id=st.session_state.get("web_form_registro_id"),
                    )
                except Exception as exc:
                    st.error(f"Erro ao salvar fonte: {exc}")
                else:
                    st.success(f"Fonte {fonte} salva com sucesso.")
                    st.session_state["web_form_registro_id"] = None
                    st.session_state["web_form_reset_pending"] = True
                    st.rerun()

    if st.session_state.get("web_form_registro_id"):
        if st.button("Cancelar edição", key="web_cancel_edit"):
            st.session_state["web_form_registro_id"] = None
            st.session_state["web_form_reset_pending"] = True
            st.rerun()

    registros = list_web_sources(active_only=False)
    paginated, page, start, end = paginate(registros, "page_web")
    st.write(f"Exibindo {start+1} a {end} de {len(registros)}")
    render_pagination_controls("page_web", page, end, len(registros), "web_prev", "web_next", size_key="page_web_size")

    if paginated:
        header = st.columns([2,3,3,1,1,1])
        header[0].markdown("**Tipo**")
        header[1].markdown("**Fonte**")
        header[2].markdown("**Descrição**")
        header[3].markdown("**Status**")
        header[4].markdown("**Editar**")
        header[5].markdown("**Excluir**")
        for row in paginated:
            cols = st.columns([2,3,3,1,1,1])
            cols[0].markdown(row.get('fowe_tipo',''))
            cols[1].markdown(row.get('fowe_fonte',''))
            cols[2].markdown(row.get('fowe_descricao',''))
            cols[3].markdown(status_badge(bool(row.get('fowe_status',0))), unsafe_allow_html=True)
            if cols[4].button("✏️", key=f"web_edit_{row.get('fowe_id', row.get('fowe_fonte', ''))}", help="Editar fonte"):
                st.session_state.web_edit_confirm = row.get('fowe_id', None)
            if cols[5].button("🗑️", key=f"web_delete_{row.get('fowe_id', row.get('fowe_fonte', ''))}", help="Excluir fonte"):
                st.session_state.web_delete_confirm = row.get('fowe_id', None)

    if st.session_state.get("web_edit_confirm") is not None:
        edit_id = st.session_state.web_edit_confirm
        edit_row = next((r for r in registros if r.get('fowe_id', None) == edit_id), None)
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

    if st.session_state.get("web_delete_confirm") is not None:
        del_id = st.session_state.web_delete_confirm
        del_row = next((r for r in registros if r.get('fowe_id', None) == del_id), None)
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
