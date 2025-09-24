from __future__ import annotations

import streamlit as st
from typing import Any, Iterable, Tuple


def status_badge(is_active: bool) -> str:
    color = "#27ae60" if is_active else "#c0392b"
    text = "Ativo" if is_active else "Inativo"
    return (
        f'<span style="color: white; background: {color}; padding: 2px 8px; '
        f'border-radius: 8px; font-size: 0.9em;">{text}</span>'
    )


def _current_page_size(size_key: str, default: int = 10) -> int:
    """Read-only: obtém o tamanho atual da página sem setar Session State."""
    return int(st.session_state.get(size_key, default) or default)


def paginate(items: list[dict[str, Any]], page_key: str, page_size: int | None = None) -> Tuple[list[dict[str, Any]], int, int, int]:
    size_key = f"{page_key}_size"
    size = page_size if page_size is not None else _current_page_size(size_key)
    page = st.session_state.get(page_key, 0)
    total = len(items)
    max_page = max(0, (total - 1) // size) if total else 0
    if page > max_page:
        page = max_page
        st.session_state[page_key] = page
    start = page * size
    end = min(start + size, total)
    return items[start:end], page, start, end


def render_pagination_controls(
    page_key: str,
    page: int,
    end: int,
    total: int,
    prev_key: str,
    next_key: str,
    size_key: str | None = None,
) -> None:
    st.divider()
    # Usar colunas laterais como espaçadores e controles centralizados
    spacer_left, controls, spacer_right = st.columns([2, 8, 2])
    with controls:
        c1, c2, c3, c4, c5 = st.columns([2,1,1,1,2])
        with c1:
            if st.button("Página anterior", disabled=page == 0, key=prev_key):
                st.session_state[page_key] = max(page - 1, 0)
                st.rerun()
        with c2:
            size_key_resolved = size_key or f"{page_key}_size"
            size = _current_page_size(size_key_resolved)
            total_pages = max(1, (total + size - 1) // size)
            target = st.number_input(
                "Ir para página",
                min_value=1,
                max_value=total_pages,
                value=(page + 1) if total_pages else 1,
                key=f"{page_key}_jump",
                step=1,
                format="%d",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("→", key=f"{page_key}_go", width='stretch'):
                st.session_state[page_key] = int(target) - 1
                st.rerun()
        with c4:
            if st.button("Próxima página", disabled=end >= total, key=next_key):
                st.session_state[page_key] = page + 1
                st.rerun()
        with c5:
            options = [5, 10, 20, 50]
            resolved_key = size_key or f"{page_key}_size"
            current = _current_page_size(resolved_key)
            has_value = resolved_key in st.session_state
            if has_value:
                st.selectbox(
                    "Itens por página",
                    options=options,
                    label_visibility="collapsed",
                    key=resolved_key,
                )
            else:
                default_index = options.index(current) if current in options else options.index(10)
                st.selectbox(
                    "Itens por página",
                    options=options,
                    index=default_index,
                    label_visibility="collapsed",
                    key=resolved_key,
                )
            new_value = _current_page_size(resolved_key)
            if new_value != current:
                st.session_state[page_key] = 0
                st.rerun()
