from __future__ import annotations

import streamlit as st
from app.domain.entities import LLMModel
from app.domain.llm_service import list_llm_models, register_llm_model, delete_llm_model
from .ui_helpers import status_badge, paginate, render_pagination_controls


STATE_DEFAULTS = {
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


def ensure_state() -> None:
    for k, v in STATE_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def apply_prefill_and_resets() -> None:
    if st.session_state.get("llm_form_reset_pending"):
        st.session_state.llm_form_model_id = None
        st.session_state.llm_form_provedor = ""
        st.session_state.llm_form_modelo = ""
        st.session_state.llm_form_api_key = ""
        st.session_state.llm_form_status = True
        st.session_state["llm_form_reset_pending"] = False
    prefill = st.session_state.get("llm_form_prefill")
    if prefill:
        st.session_state.llm_form_model_id = prefill.get("id")
        st.session_state.llm_form_provedor = prefill.get("provedor", "")
        st.session_state.llm_form_modelo = prefill.get("modelo", "")
        st.session_state.llm_form_api_key = prefill.get("api_key", "")
        st.session_state.llm_form_status = bool(prefill.get("status", 1))
        st.session_state["llm_form_prefill"] = None


def render() -> None:
    ensure_state()
    apply_prefill_and_resets()

    st.header("Cadastro de Modelos LLM")

    with st.form("llm_form"):
        provedor = st.text_input("Provedor", key="llm_form_provedor", placeholder="OPENAI")
        modelo = st.text_input("Modelo", key="llm_form_modelo", placeholder="gpt-5-nano")
        api_key = st.text_input("API Key", key="llm_form_api_key", type="password")
        ativo = st.checkbox("Ativo", key="llm_form_status")
        label = "Atualizar modelo" if st.session_state.get("llm_form_model_id") is not None else "Salvar modelo"
        salvar = st.form_submit_button(label, type="primary")
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

    if st.session_state.get("llm_form_model_id") is not None:
        if st.button("Cancelar edição", key="llm_cancel_edit"):
            st.session_state["llm_form_reset_pending"] = True
            st.rerun()

    registros = list_llm_models()
    paginated, page, start, end = paginate(registros, "page_llm")
    st.write(f"Exibindo {start+1} a {end} de {len(registros)}")
    render_pagination_controls("page_llm", page, end, len(registros), "llm_prev", "llm_next", size_key="page_llm_size")

    if paginated:
        header = st.columns([2, 2, 3, 1, 2, 1, 1])
        header[0].markdown("**Provedor**")
        header[1].markdown("**Modelo**")
        header[2].markdown("**API Key**")
        header[3].markdown("**Status**")
        header[4].markdown("**Data de criação**")
        header[5].markdown("**Editar**")
        header[6].markdown("**Excluir**")
        for row in paginated:
            cols = st.columns([2, 2, 3, 1, 2, 1, 1])
            cols[0].markdown(row["provedor"])
            cols[1].markdown(row["modelo"])
            cols[2].markdown(f"`{row['api_key']}`")
            cols[3].markdown(status_badge(row["status"]), unsafe_allow_html=True)
            cols[4].markdown(row["created_at"])
            if cols[5].button("✏️", key=f"llm_edit_{row['id']}", help="Editar modelo"):
                st.session_state.llm_edit_confirm = row['id']
            if cols[6].button("🗑️", key=f"llm_delete_{row['id']}", help="Excluir modelo"):
                st.session_state.llm_delete_confirm = row['id']

    if st.session_state.get("llm_edit_confirm") is not None:
        edit_id = st.session_state.llm_edit_confirm
        edit_row = next((r for r in registros if r["id"] == edit_id), None)
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

    if st.session_state.get("llm_delete_confirm") is not None:
        del_id = st.session_state.llm_delete_confirm
        del_row = next((r for r in registros if r["id"] == del_id), None)
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
